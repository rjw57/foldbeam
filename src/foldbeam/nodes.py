from _gdal import create_render_dataset, transform_envelope
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
        """envelope is a tuple giving (left, top, width, height) of the raster.

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
        proj_range = min(envelope[2:])

        # Giving a rough tile size in projection coordinate of...
        zoomed_tile_size = map(lambda x: abs(x[0])/x[1], zip(envelope[2:], n_tiles))
        
        # And convert to a zoom
        zooms = map(lambda x: math.log(x[0], 2) - math.log(x[1], 2), zip(self.proj_size, zoomed_tile_size))

        # Choose an overall zoom from these
        return int(math.floor(max(zooms)))

    def render(self, envelope, srs, size=None):
        # Get the destination raster
        raster = super(TileStacheRasterNode, self).render(envelope, srs, size)
        size = (raster.RasterXSize, raster.RasterYSize)

        # Convert the envelope into the preferred srs
        pref_envelope = transform_envelope(envelope, srs, self.preferred_srs,
                min(map(abs, envelope[2:])) / float(max(size)))
        zoom = self._zoom_for_envelope(pref_envelope, size)

        # Get the minimum and maximum projection coords
        min_pref = [min(pref_envelope[i], pref_envelope[i]+pref_envelope[i+2]) for i in xrange(2)]
        max_pref = [max(pref_envelope[i], pref_envelope[i]+pref_envelope[i+2]) for i in xrange(2)]

        # How many tiles in x and y at that zoom?
        n_proj_tiles = math.pow(2, zoom)

        # Convert min and max projection coords to tile coords
        min_norm = [n_proj_tiles * (x[0]-x[1])/x[2] for x in zip(min_pref, self.proj_origin, self.proj_axes)]
        max_norm = [n_proj_tiles * (x[0]-x[1])/x[2] for x in zip(max_pref, self.proj_origin, self.proj_axes)]

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
        for r in xrange(top_left.row-1, bottom_right.row+1):
            # skip out of range tile co-ords
            if r < 0 or r >= math.pow(2, zoom):
                continue
            for c in xrange(top_left.column-1, bottom_right.column+1):
                # skip out of range tile co-ords
                if c < 0 or c >= math.pow(2, zoom):
                    continue

                tile_coord = Coordinate(r, c, zoom)
                tile_tl_point = self.layer.projection.coordinateProj(tile_coord)
                tile_br_point = self.layer.projection.coordinateProj(tile_coord.right().down())

                try:
                    _, png_data = TileStache.getTile(self.layer, tile_coord, 'PNG')
                except IOError as e:
                    print('Ignoring error fetching tile %s (%s).' % (tile_coord, e))
                    continue

                gdal.FileFromMemBuffer('/vsimem/tmptile.png', png_data)

                tile_raster = gdal.Open('/vsimem/tmptile.png')
                tile_raster.SetProjection(self.preferred_srs_wkt)

                xscale = (tile_br_point.x - tile_tl_point.x) / tile_raster.RasterXSize
                yscale = (tile_br_point.y - tile_tl_point.y) / tile_raster.RasterYSize
                tile_raster.SetGeoTransform((
                    tile_tl_point.x, xscale, 0.0,
                    tile_tl_point.y, 0.0, yscale,
                ))

                gdal.ReprojectImage(tile_raster, raster, self.preferred_srs_wkt, desired_srs_wkt, gdal.GRA_Bilinear)

                gdal.Unlink('/vsimem/tmptile.png')

        return raster
