from _gdal import create_render_dataset, transform_envelope
from core import Envelope
import math
from ModestMaps.Core import Point, Coordinate
from osgeo import gdal
from osgeo.osr import SpatialReference
import StringIO
import TileStache

class Node(object):
    pass

class UnsupportedSpatialReferenceError(Exception):
    pass

class RasterNode(object):

    def render(self, envelope, srs, size=None):
        """envelope is an instance of core.Envelope giving the (left, top, width, height) of the raster.

        srs is the spatial reference associated with the co-ordinates described in envelope

        If size is not None, it is a tuple giving (width, height) of the raster in pixels. If None, the width and height
        is taken directly from the envelope.
        
        Return a dataset providing a view into this raster with the specified bounds in the spatial reference system.

        Raises an UnsupportedSpatialReferenceError if the spatial reference is unsupported.
        """

        return create_render_dataset(envelope, srs, size)

class TileStacheRasterNode(RasterNode):
    def __init__(self, layer):
        super(TileStacheRasterNode, self).__init__()

        self.layer = layer
        self.preferred_srs = SpatialReference()
        self.preferred_srs.ImportFromProj4(layer.projection.srs)
        self.preferred_srs_wkt = self.preferred_srs.ExportToWkt()

        # Calculate the bounds of the zoom level 0 tile
        bounds = [
            self.layer.projection.coordinateProj(Coordinate(0,0,0)),
            self.layer.projection.coordinateProj(Coordinate(1,1,0)),
        ]

        self.proj_axes = (bounds[1].x - bounds[0].x, bounds[1].y - bounds[0].y)
        self.proj_size = map(abs, self.proj_axes)
        self.proj_origin = (bounds[0].x, bounds[0].y)

        min_x = min([p.x for p in bounds])
        max_x = max([p.x for p in bounds])
        min_y = min([p.y for p in bounds])
        max_y = max([p.y for p in bounds])

        self.proj_bounds = (min_x, min_y, max_x-min_x, max_y-min_y)

    def _zoom_for_envelope(self, envelope, size):
        # How many tiles should cover each axis
        n_tiles = map(lambda x: x/256.0, size)

        # Over what range?
        envelope_size = map(abs, envelope.offset())
        proj_range = min(envelope_size)

        # Giving a rough tile size in projection coordinate of...
        zoomed_tile_size = map(lambda x: x[0]/x[1], zip(envelope_size, n_tiles))
    
        # And convert to a zoom
        zooms = map(lambda x: math.log(x[0], 2) - math.log(x[1], 2), zip(self.proj_size, zoomed_tile_size))

        # Which is closer to the precise zoom we want?
        zoom = max(zooms)

        floor_diff = abs(math.pow(2, zoom) - math.pow(2, math.floor(zoom)))
        ceil_diff = abs(math.pow(2, zoom) - math.pow(2, math.ceil(zoom)))

        # Choose an overall zoom from these
        return int(math.ceil(zoom)) if ceil_diff < floor_diff else int(math.floor(zoom))

    def render(self, envelope, srs, size=None):
        if size is None:
            size = map(abs, envelope[2:])

        envelope_size = map(abs, envelope.offset())
        pref_envelope = transform_envelope(
                envelope, srs, self.preferred_srs,
                min(envelope_size) / float(max(size)))
        zoom = self._zoom_for_envelope(pref_envelope, size)

        if size[0] <= 256 and size[1] <= 256:
            return self._render_tile(self, envelope, srs, size, zoom)

        raster = create_render_dataset(envelope, srs, size)
        assert(raster.RasterXSize == size[0])
        assert(raster.RasterYSize == size[1])
        xscale, yscale = [x[0] / float(x[1]) for x in zip(envelope.offset(), size)]

        max_size = 256
        for x in xrange(0, size[0], max_size):
            width = min(x + max_size, size[0]) - x
            for y in xrange(0, size[1], max_size):
                height = min(y + max_size, size[1]) - y
                tile_envelope = Envelope(
                        envelope.left + xscale * x,
                        envelope.left + xscale * (x + width),
                        envelope.top + yscale * y,
                        envelope.top + yscale * (y + height),
                )
                tile_raster = self._render_tile(tile_envelope, srs, (width, height), zoom)
                tile_data = tile_raster.ReadRaster(0, 0, width, height)
                raster.WriteRaster(x, y, width, height, tile_data)
        
        return raster

    def _render_tile(self, envelope, srs, size, zoom):
        # Get the destination raster
        raster = create_render_dataset(envelope, srs, size)
        assert size == (raster.RasterXSize, raster.RasterYSize)

        # Convert the envelope into the preferred srs
        envelope_size = map(abs, envelope.offset())
        pref_envelope = transform_envelope(
                envelope, srs, self.preferred_srs,
                min(envelope_size) / float(max(size)))

        # Get the minimum and maximum projection coords
        min_pref = (min(pref_envelope.left, pref_envelope.right), min(pref_envelope.top, pref_envelope.bottom))
        max_pref = (max(pref_envelope.left, pref_envelope.right), max(pref_envelope.top, pref_envelope.bottom))

        # How many tiles overall in x and y at the zoom level?
        n_proj_tiles = math.pow(2, zoom)

        # Convert min and max projection coords to tile coords
        min_norm = [n_proj_tiles * (x[0]-x[1])/x[2] for x in zip(min_pref, self.proj_origin, self.proj_axes)]
        max_norm = [n_proj_tiles * (x[0]-x[1])/x[2] for x in zip(max_pref, self.proj_origin, self.proj_axes)]

        xtile_size = self.proj_axes[0] / n_proj_tiles
        ytile_size = self.proj_axes[1] / n_proj_tiles

        # Get tile coords
        top_left = Coordinate(
                int(math.floor(min(min_norm[1], max_norm[1]))),
                int(math.floor(min(min_norm[0], max_norm[0]))), zoom)
        bottom_right = Coordinate(
                int(math.ceil(max(min_norm[1], max_norm[1]))),
                int(math.ceil(max(min_norm[0], max_norm[0]))), zoom)

        # Get each tile image
        png_driver = gdal.GetDriverByName('PNG')
        desired_srs_wkt = srs.ExportToWkt()
        assert png_driver is not None
        for r in xrange(top_left.row, bottom_right.row+1):
            if r < 0 or r >= n_proj_tiles:
                continue
            for c in xrange(top_left.column, bottom_right.column+1):
                c = c % n_proj_tiles
                if c < 0:
                    c = c + n_proj_tiles

                tile_coord = Coordinate(r, c, zoom)
                tile_tl_point = self.layer.projection.coordinateProj(tile_coord)
                tile_br_point = Point(tile_tl_point.x + xtile_size, tile_tl_point.y + ytile_size)

                try:
                    tile_type, png_data = TileStache.getTile(self.layer, tile_coord, 'png')
                    if tile_type != 'image/png':
                        print('Did not get PNG data when fetching tile %s. Skipping.' % (tile_coord))
                        continue
                except IOError as e:
                    print('Ignoring error fetching tile %s (%s).' % (tile_coord, e))
                    continue

                gdal.FileFromMemBuffer('/vsimem/tmptile.png', png_data)

                tile_raster = gdal.Open('/vsimem/tmptile.png')
                tile_raster.SetProjection(self.preferred_srs_wkt)

                xscale = xtile_size / (tile_raster.RasterXSize-1)
                yscale = ytile_size / (tile_raster.RasterYSize-1)
                tile_raster.SetGeoTransform((
                    tile_tl_point.x, xscale, 0.0,
                    tile_tl_point.y, 0.0, yscale,
                ))

                gdal.ReprojectImage(tile_raster, raster, self.preferred_srs_wkt, desired_srs_wkt, gdal.GRA_Bilinear)

                gdal.Unlink('/vsimem/tmptile.png')

        return raster
