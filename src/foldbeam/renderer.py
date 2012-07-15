from functools import wraps
import math
import logging
import StringIO
import sys

import cairo
from concurrent import futures
import numpy as np
from osgeo import gdal, gdal_array
from osgeo.ogr import CreateGeometryFromWkt
from osgeo.osr import SpatialReference
from PIL import Image
import httplib2
import TileStache

from foldbeam.core import RendererBase, set_geo_transform, boundary_from_envelope, Envelope

log = logging.getLogger()

def _cairo_surface_from_data(data):
    # load via the PIL
    image = Image.open(StringIO.StringIO(data)).convert('RGBA')
    imw, imh = image.size

    # swizzle RGBA -> BGRA
    image = Image.frombuffer('RGBA', (imw, imh), image.tostring(), 'raw', 'BGRA', 0, 1)

    # write into a Cairo surface
    surface = cairo.ImageSurface.create_for_data(np.array(image), cairo.FORMAT_ARGB32, imw, imh)

    return surface

class URLFetchError(Exception):
    """An error raised by a custom URL fetchber for TileFetcher if the URL could not be fetchbed."""
    pass


def default_url_fetcher(url):
    """The default URL fetcher to use in :py:class:`TileFetcher`. If there is an error fetching the URL a URLFetchError
    is raised.

    """
    http = httplib2.Http()
    rep, content = http.request(url, 'GET')
    if rep.status != 200:
        raise URLFetchError(str(rep.status) + ' ' + rep.reason)
    return content

class ProjectionError(Exception):
    pass

def _image_surface_to_array(image_surface):
    """Return a numpy array pointing to a Cairo image surface

    """
    assert(image_surface.get_format() == cairo.FORMAT_ARGB32)
    array = np.frombuffer(image_surface.get_data(), np.uint8)
    array.shape = (image_surface.get_height(), image_surface.get_width(), 4)
    return array

def _image_surface_to_dataset(image_surface):
    """Return a GDAL dataset pointing to a Cairo image surface.

    You may still need to set the geo transform for the dataset

    """

    assert(image_surface.get_format() == cairo.FORMAT_ARGB32)

    # Firtly get the surface as an array
    image_array = _image_surface_to_array(image_surface)

    dataset = gdal_array.OpenArray(np.rollaxis(image_array, 2))
    dataset.GetRasterBand(1).SetColorInterpretation(gdal.GCI_BlueBand)
    dataset.GetRasterBand(2).SetColorInterpretation(gdal.GCI_GreenBand)
    dataset.GetRasterBand(3).SetColorInterpretation(gdal.GCI_RedBand)
    dataset.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)

    return dataset

def reproject_from_native_spatial_reference(f):
    """Wrap a rendering method by reprojecting rasterised images from a renderer which can handle only one spatial
    reference.

    The object with the wrapped rendering method *must* have an attribute called :py:attr:`native_spatial_reference`
    which is an instance of :py:class:`osgeo.osr.SpatialReference` giving the native spatial reference for that renderer.

    """

    @wraps(f)
    def render(self, context, spatial_reference=None, **kwargs):
        # Find the native spatial reference
        native_spatial_reference = self.native_spatial_reference
        assert(native_spatial_reference is not None)

        # If no spatial reference was specified, or if it matches the native one, just render directly
        if spatial_reference is None or spatial_reference.IsSame(native_spatial_reference):
            return f(self, context, native_spatial_reference, **kwargs)

        log.info('Reprojecting from native SRS:')
        log.info(native_spatial_reference.ExportToWkt())
        log.info('to:')
        log.info(spatial_reference.ExportToWkt())

        # Construct a polygon representing the current clip area's extent
        target_min_x, target_min_y, target_max_x, target_max_y = context.clip_extents()

        wkt = 'POLYGON ((%s))' % (
                ','.join(['%f %f' % x for x in [
                    (target_min_x,target_min_y),
                    (target_max_x,target_min_y),
                    (target_max_x,target_max_y),
                    (target_min_x,target_max_y),
                    (target_min_x,target_min_y)
                ]]),
        )
        geom = CreateGeometryFromWkt(wkt)
        geom.AssignSpatialReference(spatial_reference)

        # segmentise the geometry to the scale of one device pixel
        seg_len = min(*[abs(x) for x in context.device_to_user_distance(1,1)])
        geom.Segmentize(seg_len)

        # compute a rough resolution for the intermediate based on the segment length and clip extents
        intermediate_size = (
            int(math.ceil(abs(target_max_x - target_min_x) / seg_len)),
            int(math.ceil(abs(target_max_y - target_min_y) / seg_len)),
        )

        # transform the geometry to the native spatial reference
        old_opt = gdal.GetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION')
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', 'TRUE')
        err = geom.TransformTo(native_spatial_reference)
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', old_opt)
        if err != 0:
            raise ProjectionError('Unable to project boundary into target projection: ' + str(err))

        # get the envelope of the clip area in the native spatial reference
        native_min_x, native_max_x, native_min_y, native_max_y = geom.GetEnvelope()

        # create a cairo image surface for the intermediate
        intermediate_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, intermediate_size[0], intermediate_size[1])
        intermediate_context = cairo.Context(intermediate_surface)
        set_geo_transform(
                intermediate_context,
                native_min_x, native_max_x, native_max_y, native_min_y,
                intermediate_size[0], intermediate_size[1]
        )

        # render the intermediate
        f(self, intermediate_context, native_spatial_reference, **kwargs)

        # get hold of the intermediate surface as a dataset
        intermediate_dataset = _image_surface_to_dataset(intermediate_surface)
        assert intermediate_dataset is not None
        intermediate_dataset.SetGeoTransform((
            native_min_x, (native_max_x-native_min_x) / float(intermediate_size[0]), 0.0, 
            native_max_y, 0.0, -(native_max_y-native_min_y) / float(intermediate_size[1]),
        ))

        # create an output dataset
        output_pixel_size = context.device_to_user_distance(1,1)
        output_width = int(math.ceil(abs(target_max_x - target_min_x) / abs(output_pixel_size[0])))
        output_height = int(math.ceil(abs(target_max_y - target_min_y) / abs(output_pixel_size[1])))
        driver = gdal.GetDriverByName('MEM')
        assert driver is not None
        output_dataset = driver.Create('', output_width, output_height, 4, gdal.GDT_Byte)
        assert output_dataset is not None
        output_dataset.SetGeoTransform((
            target_min_x, abs(output_pixel_size[0]), 0.0,
            target_max_y, 0.0, -abs(output_pixel_size[1]),
        ))

        # project intermediate into output
        gdal.ReprojectImage(
                intermediate_dataset, output_dataset,
                native_spatial_reference.ExportToWkt(), spatial_reference.ExportToWkt(),
                gdal.GRA_Bilinear
        )

        # create a cairo image surface for the output. This unfortunately necessitates a copy since the in-memory format
        # for a GDAL Dataset is not interleaved.
        output_array = np.transpose(output_dataset.ReadAsArray(), (1,2,0))
        output_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, output_width, output_height)
        surface_array = np.frombuffer(output_surface.get_data(), dtype=np.uint8)
        surface_array[:] = output_array.flat
        output_surface.mark_dirty()

        # draw the transformed output to the context
        context.set_source_surface(output_surface)
        context.get_source().set_matrix(cairo.Matrix(
            xx = 1.0 / abs(output_pixel_size[0]),
            yy = -1.0 / abs(output_pixel_size[1]),
            x0 = -target_min_x / abs(output_pixel_size[0]),
            y0 = -target_max_y / -abs(output_pixel_size[1]),
        ))

        # draw the tile itself. We disable antialiasing because if the tile slightly overlaps an output
        # pixel we want the interpolation of the tile to do the smoothing, not the rasteriser
        context.save()
        context.set_antialias(cairo.ANTIALIAS_NONE)
        context.rectangle(target_min_x, target_min_y, target_max_x - target_min_x, target_max_y - target_min_y)
        context.fill()
        context.restore()

    return render

class TileFetcher(RendererBase):
    """Render from slippy map tile URLs.

    This is somewhat incomplete at the moment. Given a Google/Bing/OSM-style slippy map tile URL pattern of the form
    ``http://server/path/to/tiles/{zoom}/{x}/{y}.format``, this renderer can render the tiles to a Cairo context.

    .. note::
        If no spatial reference is specified, it will default to EPSG:3857. Similarly, if no bounds are specified, the
        default is to assume the bounds of this projection (x and y being +/- 20037508.34 metres).

    The default URL pattern is ``http://otile1.mqcdn.com/tiles/1.0.0/osm/{zoom}/{x}/{y}.jpg`` which will load tiles
    from the MapQuest servers.

    If the *url_fetcher* parameter is specified, it is a callable which takes a single string giving a URL as the first
    argument and returns a sequence of bytes for the URL contents. It can raise URLFetchError if the resource is not
    available. If no fetcher is provided, :py:func:`default_url_fetcher` is used. The fetcher callable must be
    thread-safe.
    
    :param url_pattern: default is to use MapQuest, a pattern for calculating the URL to load tiles from
    :type url_pattern: string
    :param spatial_reference: default EPSG:3857, the native spatial reference for the tiles
    :type spatial_reference: osgeo.osr.SpatialReference or None
    :param tile_size: default (256, 256), the width and height of one tile in pixels
    :type tile_size: tuple of integer or None
    :param bounds: default as noted above, the left, right, top and bottom boundary of the projection
    :type bounds: tuple of float or None
    :param url_fetcher: which callable to use for URL fetching
    :type url_fetcher: callable or None
    """

    def __init__(self, url_pattern=None, spatial_reference=None, tile_size=None, bounds=None, url_fetcher=None):
        super(TileFetcher, self).__init__()
        self.url_pattern = url_pattern or 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{zoom}/{x}/{y}.jpg'
        self.tile_size = tile_size or (256, 256)

        self.bounds = bounds or (-20037508.34, 20037508.34, 20037508.34, -20037508.34)
        self.bounds_size = (abs(self.bounds[1] - self.bounds[0]), abs(self.bounds[3] - self.bounds[2]))

        if spatial_reference is not None:
            self.native_spatial_reference = spatial_reference
        else:
            self.native_spatial_reference = SpatialReference()
            self.native_spatial_reference.ImportFromEPSG(3857)

        self._fetch_url = url_fetcher or default_url_fetcher

    @reproject_from_native_spatial_reference
    def render(self, context, spatial_reference=None):
        if spatial_reference is not None and not spatial_reference.IsSame(self.native_spatial_reference):
            raise ValueError('TileFetcher asked to render tile from incompatible spatial reference.')

        # Calculate the distance in projection co-ordinates of one device pixel
        pixel_size = context.device_to_user_distance(1,1)

        # And hence the size in projection co-ordinates of one tile
        ideal_tile_size = tuple([abs(x[0] * x[1]) for x in zip(pixel_size, self.tile_size)])

        # How many math.powers of two smaller than the bounds is this?
        ideal_zoom = tuple([math.log(x[0],2) - math.log(x[1],2) for x in zip(self.bounds_size, ideal_tile_size)])

        # What zoom will we *actually* use
        zoom = max(0, int(round(max(*ideal_zoom))))

        # How many tiles at this zoom level?
        n_tiles = 1<<zoom

        # Calculate the tile co-ordinates for the clip area extent
        min_px, min_py, max_px, max_py = context.clip_extents()

        # This give tile co-ordinates for the extremal tiles
        tl = [int(math.floor(x)) for x in self._projection_to_tile(min_px, max_py, zoom)]
        br = [int(math.floor(x)) for x in self._projection_to_tile(max_px, min_py, zoom)]

        # extract the minimum/maximum x/y co-ordinate for the tiles
        min_x, min_y = tl
        max_x, max_y = br

        # kick off requests for the tiles (maximum 4 concurrent requests)
        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            # we will load tiles in a thread pool with a maximum of 10 workers for a maximum of 10 concurrent requests
            future_to_tile = {}

            for x in range(min_x, max_x+1):
                # wrap the x co-ordinate in the number of tiles
                wrapped_x = x % n_tiles
                if wrapped_x < 0:
                    wrapped_x += n_tiles

                for y in range(min_y, max_y+1):
                    # skip out of range y-tiles
                    if y < 0 or y >= n_tiles:
                        continue

                    url = self.url_pattern.format(x=wrapped_x, y=y, zoom=zoom)

                    future = executor.submit(self._fetch_url, url)
                    future_to_tile[future] = (x,y,url)

            # render the tiles as they come in
            for future in futures.as_completed(future_to_tile):
                x, y, url = future_to_tile[future]
                if future.exception():
                    import traceback
                    log.error("error loading '{url}':".format(url=url))
                    e = future.exception()
                    for line in traceback.format_exception_only(type(e), e):
                        log.error('    ' + line)
                else:
                    # load the tile into a cairo surface
                    data = future.result()
                    surface = _cairo_surface_from_data(data)

                    # what extents should this tile have?
                    tile_x, tile_y, tile_w, tile_h = self._tile_extents(x, y, zoom)

                    tile_x_scale = surface.get_width() / tile_w
                    tile_y_scale = -surface.get_height() / tile_h

                    # set up the tile as a source
                    context.set_source_surface(surface)
                    context.get_source().set_matrix(cairo.Matrix(
                        xx = tile_x_scale,
                        yy = tile_y_scale,
                        x0 = -tile_x * tile_x_scale,
                        y0 = -tile_y * tile_y_scale + surface.get_height()
                    ))

                    # we need to set the extend options to avoid interpolating towards zero-alpha at the edges
                    context.get_source().set_extend(cairo.EXTEND_PAD)

                    # draw the tile itself. We disable antialiasing because if the tile slightly overlaps an output
                    # pixel we want the interpolation of the tile to do the smoothing, not the rasteriser
                    context.save()
                    context.set_antialias(cairo.ANTIALIAS_NONE)
                    context.rectangle(tile_x, tile_y, tile_w, tile_h)
                    context.fill()
                    context.restore()


    def _tile_extents(self, tx, ty, zoom):
        """Return a tuple (minx, miny, width, height) giving the extents of a tile in projection co-ords."""

        # Calculate size of one tile in projection co-ordinates
        tile_size = tuple([math.pow(2.0, math.log(x,2) - zoom) for x in self.bounds_size])

        left = tx * tile_size[0] + self.bounds[0]
        top = self.bounds[2] - ty * tile_size[1]
        return (left, top-tile_size[1], tile_size[0], tile_size[1])

    def _projection_to_tile(self, px, py, zoom):
        """Convert from a projection co-ordinate to a tile co-ordinate. The tile co-ordinate system has an origin in the
        top-left hand corner.

        """

        # Calculate size of one tile in projection co-ordinates
        tile_size = tuple([x / math.pow(2.0, zoom) for x in self.bounds_size])

        # Map projection co-ords into tile co-ords
        return tuple([x[0] / x[1] for x in zip((px-self.bounds[0], self.bounds[2]-py), tile_size)])

class TileStacheProvider(object):
    """An object suitable for use as a TileStache provider.

    .. py:attribute:: renderer

        Set this attribute to a renderer instance to use for rendering map tiles.
    """
    def __init__(self, layer):
        super(TileStacheProvider, self).__init__()
        self.renderer = TileFetcher()

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = SpatialReference()

        # this is a special HACK to take account of the fact that the proj4 srs provided by TileStache has the +over
        # parameter and OGR thinks it is different to EPSG:3857
        if srs == TileStache.Geography.SphericalMercator.srs:
            spatial_reference.ImportFromEPSG(3857)
        else:
            spatial_reference.ImportFromProj4(srs)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        set_geo_transform(cr, xmin, xmax, ymax, ymin, width, height)
        self.renderer.render(cr, spatial_reference=spatial_reference)

        im = Image.frombuffer('RGBA', (width, height), surface.get_data(), 'raw', 'BGRA', 0, 1)
        return im

class GeometryRenderer(RendererBase):
    """Render shapely geometric shapes into a context.

    If keyword arguments are supplied, set the attributes listed below.

    .. py:attribute:: geom

        Default None. An object which yields a set of geometry to render. For example,
        :py:class:`foldbeam.geometry.IterableGeometry`.

    .. py:attribute:: marker_radius

        Default 5. The radius, in projection co-ordinates, of the point marker.

    .. py:attribute:: stroke

        Default True. If True, call 'stroke()' to draw the outline of geometry.

    .. py:attribute:: fill

        Default False. If True, call 'fill()' to fill the geometry. If both :py:attr:`fill` and :py:attr:`stroke` are
        True, then filling happens first.

    """
    def __init__(self, **kwargs):
        super(GeometryRenderer, self).__init__()
        self.geom = None
        self.marker_radius = 5
        self.stroke = True
        self.fill = False

        for k, v in kwargs.iteritems():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise AttributeError(k)

    def render(self, context, spatial_reference=None):
        if self.geom is None:
            return

        if not self.stroke and not self.fill:
            return

        minx, miny, maxx, maxy = context.clip_extents()
        boundary = boundary_from_envelope(Envelope(minx, maxx, maxy, miny, spatial_reference))

        for g in self.geom.within(boundary, spatial_reference):
            if g.geom_type == 'Point':
                self._render_point(g, context)
            elif g.geom_type == 'MultiPoint':
                [self._render_point(x, context) for x in g]
            elif g.geom_type == 'LineString':
                self._render_line_string(g, context)
            elif g.geom_type == 'MultiLineString':
                [self._render_line_string(x, context) for x in g]
            elif g.geom_type == 'LinearRing':
                self._render_line_string(g, context, close_path=True)
            elif g.geom_type == 'Polygon':
                self._render_polygon(g, context)
            elif g.geom_type == 'MultiPolygon':
                [self._render_polygon(x, context) for x in g]
            else:
                log.warning('Unknown geometry type: ' + str(g.geom_type))

    def _stroke_and_or_fill(self, context):
        if self.fill and not self.stroke:
            context.fill()
        elif self.fill and self.stroke:
            context.fill_preserve()
            context.stroke()
        elif self.stroke:
            context.stroke()

    def _render_point(self, p, context):
        context.arc(p.x, p.y, self.marker_radius, 0, math.pi * 2.0)
        self._stroke_and_or_fill(context)

    def _path(self, ls, context, close_path=False):
        xs, ys = ls.xy
        if len(xs) == 0:
            return
        context.move_to(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            context.line_to(x, y)
        if close_path:
            context.close_path()

    def _render_line_string(self, ls, context, close_path=False):
        self._path(ls, context, close_path)
        self._stroke_and_or_fill(context)

    def _render_polygon(self, ls, context):
        self._path(ls.exterior, context, True)
        for p in ls.interiors:
            self._path(p, context, True)
        context.save()
        context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        self._stroke_and_or_fill(context)
        context.restore()
