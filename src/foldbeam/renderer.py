import math
import logging
from urllib2 import urlopen
import StringIO
import sys

import cairo
from concurrent import futures
import numpy as np
from osgeo.osr import SpatialReference
from PIL import Image

from foldbeam.core import RendererBase

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

class TileFetcher(RendererBase):
    """Render from slippy map tile URLs.

    This is somewhat incomplete at the moment. Given a Google/Bing/OSM-style slippy map tile URL pattern of the form
    ``http://server/path/to/tiles/{zoom}/{x}/{y}.format``, this renderer can render the tiles to a Cairo context.

    .. note::
        If no spatial reference is specified, it will default to EPSG:3857. Similarly, if no bounds are specified, the
        default is to assume the bounds of this projection (x and y being +/- 20037508.34 metres).

    The default URL pattern is ``http://otile1.mqcdn.com/tiles/1.0.0/osm/{zoom}/{x}/{y}.jpg`` which will load tiles
    from the MapQuest servers.
    
    :param url_pattern: default is to use MapQuest, a pattern for calculating the URL to load tiles from
    :type url_pattern: string
    :param spatial_reference: default EPSG:3857, the native spatial reference for the tiles
    :type spatial_reference: osgeo.osr.SpatialReference or None
    :param tile_size: default (256, 256), the width and height of one tile in pixels
    :type tile_size: tuple of integer or None
    :param bounds: default as noted above, the left, right, top and bottom boundary of the projection
    :type bounds: tuple of float or None
    """

    def __init__(self, url_pattern=None, spatial_reference=None, tile_size=None, bounds=None):
        super(TileFetcher, self).__init__()
        self.url_pattern = url_pattern or 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{zoom}/{x}/{y}.jpg'
        self.tile_size = tile_size or (256, 256)

        self.bounds = bounds or (-20037508.34, 20037508.34, 20037508.34, -20037508.34)
        self.bounds_size = (abs(self.bounds[1] - self.bounds[0]), abs(self.bounds[3] - self.bounds[2]))

        if spatial_reference is not None:
            self.spatial_reference = spatial_reference
        else:
            self.spatial_reference = SpatialReference()
            self.spatial_reference.ImportFromEPSG(3857)

    def render(self, context, spatial_reference=None):
        if spatial_reference is not None and spatial_reference.IsSame(self.spatial_reference):
            raise ValueError('TileFetcher asked to render tile from incompatible spatial reference.')

        # Calculate the distance in projection co-ordinates of one device pixel
        pixel_size = context.device_to_user_distance(1,1)

        # And hence the size in projection co-ordinates of one tile
        ideal_tile_size = tuple([abs(x[0] * x[1]) for x in zip(pixel_size, self.tile_size)])

        # How many math.powers of two smaller than the bounds is this?
        ideal_zoom = tuple([math.log(x[0],2) - math.log(x[1],2) for x in zip(self.bounds_size, ideal_tile_size)])

        # What zoom will we *actually* use
        zoom = int(math.floor(min(*ideal_zoom)))

        # Calculate the tile co-ordinates for the clip area extent
        min_px, min_py, max_px, max_py = context.clip_extents()

        # This give tile co-ordinates for the extremal tiles
        bl = [int(math.floor(x)) for x in self._projection_to_tile(min_px, min_py, zoom)]
        tr = [int(math.floor(x)) for x in self._projection_to_tile(max_px, max_py, zoom)]

        # calculate the minimum/maximum x/y co-ordinate for the tiles
        min_x, min_y = [min(*x) for x in zip(bl, tr)]
        max_x, max_y = [max(*x) for x in zip(bl, tr)]

        # utility function to load a URL with urlopen
        def load_url(url, timeout):
            request = urlopen(url, timeout=timeout)
            return (request.info().gettype(), request.read())

        # we will load tiles in a thread pool with a maximum of 10 workers for a maximum of 10 concurrent requests
        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            # kick off requests for the tiles (maximum 4 concurrent requests)
            future_to_tile = {}
            for x in range(min_x, max_x+1):
                for y in range(min_y, max_y+1):
                    url = self.url_pattern.format(x=x, y=y, zoom=zoom)
                    future_to_tile[executor.submit(load_url, url, 10)] = (x,y,url)

            # render the tiles as they come in
            for future in futures.as_completed(future_to_tile):
                x, y, url = future_to_tile[future]
                if future.exception():
                    log.error("error loading '{url}'\n".format(url=url))
                else:
                    # load the tile into a cairo surface
                    _, data = future.result()
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

                    # fill the tile
                    context.rectangle(tile_x, tile_y, tile_w, tile_h)
                    context.fill()


    def _tile_extents(self, tx, ty, zoom):
        """Return a tuple (minx, miny, width, height) giving the extents of a tile in projection co-ords."""

        # Calculate size of one tile in projection co-ordinates
        tile_size = tuple([x / math.pow(2.0, zoom) for x in self.bounds_size])

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
