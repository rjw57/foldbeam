import _gdal
import core
import math
from ModestMaps.Core import Point, Coordinate
from osgeo import gdal
from osgeo.osr import SpatialReference
import StringIO
import TileStache

from graph import *

class GDALDatasetRasterNode(Node):
    def __init__(self, dataset):
        super(GDALDatasetRasterNode, self).__init__()
        self.outputs['raster'] = CallableOutputPad(self._render)
        self.dataset = dataset

    def _render(self, envelope, size=None):
        if size is None:
            size = map(int, envelope.size())

        # Get the destination raster
        raster = _gdal.create_render_dataset(
                envelope, size,
                self.dataset.RasterCount)

        desired_srs_wkt = envelope.spatial_reference.ExportToWkt()
        gdal.ReprojectImage(
                self.dataset, raster.dataset,
                self.dataset.GetProjection(),
                desired_srs_wkt,
                gdal.GRA_Bilinear)

        return ContentType.RASTER, raster

class TileStacheRasterNode(Node):
    def __init__(self, layer):
        super(TileStacheRasterNode, self).__init__()
        self.outputs['raster'] = CallableOutputPad(self._render)

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
        int_zoom = int(math.ceil(zoom)) if ceil_diff < floor_diff else int(math.floor(zoom))
        return max(0, min(18, int_zoom))

    def _render(self, envelope, size=None):
        if size is None:
            size = map(int, envelope.size())

        if size[0] <= 256 and size[1] <= 256:
            pref_envelope = envelope.transform_to(
                    self.preferred_srs,
                    min(envelope.size()) / float(max(size)))
            zoom = self._zoom_for_envelope(pref_envelope, size)
            return ContentType.RASTER, self._render_tile(envelope, size, zoom)

        raster = _gdal.create_render_dataset(envelope, size)
        assert(raster.dataset.RasterXSize == size[0])
        assert(raster.dataset.RasterYSize == size[1])
        xscale, yscale = [x[0] / float(x[1]) for x in zip(envelope.offset(), size)]

        max_size = 256
        zooms = []
        tiles = []
        for x in xrange(0, size[0], max_size):
            width = min(x + max_size, size[0]) - x
            for y in xrange(0, size[1], max_size):
                height = min(y + max_size, size[1]) - y
                tile_envelope = core.Envelope(
                        envelope.left + xscale * x,
                        envelope.left + xscale * (x + width),
                        envelope.top + yscale * y,
                        envelope.top + yscale * (y + height),
                        envelope.spatial_reference,
                )
                try:
                    pref_envelope = tile_envelope.transform_to(
                            self.preferred_srs,
                            min(tile_envelope.size()) / float(max(width, height)))
                except core.ProjectionError:
                    # Skip projection errors
                    continue
                zooms.append(self._zoom_for_envelope(pref_envelope, (width, height)))
                tiles.append((tile_envelope, (x,y), (width, height)))
        
        # Choose the 75th percentile zoom
        zooms.sort()
        zoom = zooms[(len(zooms)>>1) + (len(zooms)>>2)]

        for tile_envelope, tile_pos, tile_size in tiles:
            tile_raster = self._render_tile(tile_envelope, tile_size, zoom)
            tile_data = tile_raster.dataset.ReadRaster(0, 0, tile_size[0], tile_size[1])
            raster.dataset.WriteRaster(tile_pos[0], tile_pos[1], tile_size[0], tile_size[1], tile_data)
        
        return ContentType.RASTER, raster

    def _render_tile(self, envelope, size, zoom):
        # Get the destination raster
        raster = _gdal.create_render_dataset(envelope, size)
        assert size == (raster.dataset.RasterXSize, raster.dataset.RasterYSize)

        # Convert the envelope into the preferred spatial reference
        try:
            pref_envelope = envelope.transform_to(
                    self.preferred_srs,
                    min(envelope.size()) / float(max(size)))
        except core.ProjectionError:
            print('Ignoring projection error and returning empty raster')
            return raster

        # How many tiles overall in x and y at this zoom
        n_proj_tiles = math.pow(2, zoom)

        # Compute the tile co-ordinates of each corner
        corners = [
                self.layer.projection.projCoordinate(Point(pref_envelope.left, pref_envelope.top)),
                self.layer.projection.projCoordinate(Point(pref_envelope.right, pref_envelope.top)),
                self.layer.projection.projCoordinate(Point(pref_envelope.left, pref_envelope.bottom)),
                self.layer.projection.projCoordinate(Point(pref_envelope.right, pref_envelope.bottom)),
        ]
        corners = [c.zoomTo(zoom) for c in corners]

        corner_rows = [int(math.floor(x.row)) for x in corners]
        corner_columns = [int(math.floor(x.column)) for x in corners]

        # Get each tile image
        png_driver = gdal.GetDriverByName('PNG')
        desired_srs_wkt = envelope.spatial_reference.ExportToWkt()
        assert png_driver is not None
        for r in xrange(min(corner_rows), max(corner_rows)+1):
            if r < 0 or r >= n_proj_tiles:
                continue
            for c in xrange(min(corner_columns), max(corner_columns)+1):
                tile_tl_point = self.layer.projection.coordinateProj(Coordinate(r,c,zoom))
                tile_br_point = self.layer.projection.coordinateProj(Coordinate(r+1,c+1,zoom))

                c = c % n_proj_tiles
                if c < 0:
                    c += n_proj_tiles
                tile_coord = Coordinate(r, c, zoom)

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

                xscale = (tile_br_point.x - tile_tl_point.x) / tile_raster.RasterXSize
                yscale = (tile_br_point.y - tile_tl_point.y) / tile_raster.RasterXSize
                tile_raster.SetGeoTransform((
                    tile_tl_point.x, xscale, 0.0,
                    tile_tl_point.y, 0.0, yscale,
                ))

                gdal.ReprojectImage(
                        tile_raster, raster.dataset,
                        self.preferred_srs_wkt, desired_srs_wkt, gdal.GRA_Bilinear)

                gdal.Unlink('/vsimem/tmptile.png')

        return raster
