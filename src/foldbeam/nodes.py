import _gdal
import core
import math
from ModestMaps.Core import Point, Coordinate
from osgeo import gdal
from osgeo.osr import SpatialReference
import numpy as np
import StringIO
import TileStache

from graph import *

class LayerRasterNode(Node):
    def __init__(self, pads):
        super(LayerRasterNode, self).__init__()
        self.outputs['raster'] = CallableOutputPad(self._render)
        self.pads = pads

    def _render(self, envelope, size=None):
        if len(self.pads) == 0:
            return None

        if size is None:
            size = map(int, envelope.size())

        responses = [pad(envelope, size) for pad in self.pads]
        responses = [x for x in responses if x is not None]
        if len(responses) == 0:
            return None

        output = None
        for type_, raster in responses:
            if type_ == ContentType.NONE:
                continue

            if type_ != ContentType.RASTER:
                raise RuntimeError('Input is not raster')
            
            layer = raster.to_rgba()
            if layer is None:
                print('layer failed to convert')
                continue

            if output is None:
                output = layer
                continue

            one_minus_alpha = np.atleast_3d(1.0 - layer[:,:,3])
            
            output[:,:,:3] *= np.repeat(one_minus_alpha, 3, 2) 
            output[:,:,:3] += layer[:,:,:3]

            output[:,:,3] *= one_minus_alpha[:,:,0]
            output[:,:,3] += layer[:,:,3]

        if output is None:
            return ContentType.NONE, None

        return ContentType.RASTER, core.Raster(output, envelope, to_rgba=lambda x: x)

class GDALDatasetRasterNode(Node):
    def __init__(self, dataset):
        super(GDALDatasetRasterNode, self).__init__()
        self.outputs['raster'] = CallableOutputPad(self._render)
        self.dataset = dataset
        self.spatial_reference = SpatialReference()
        self.spatial_reference.ImportFromWkt(self.dataset.GetProjection())

        self.envelope = _gdal.dataset_envelope(self.dataset, self.spatial_reference)
        self.boundary = core.boundary_from_envelope(self.envelope)

        self.is_palette = any([
            self.dataset.GetRasterBand(i).GetColorInterpretation() == gdal.GCI_PaletteIndex
            for i in xrange(1, self.dataset.RasterCount+1)])

    def _to_rgba(self, array):
        rgba = core.to_rgba_unknown(array)
        if np.any(rgba[:,:,3] != 1.0):
            mask_alpha = rgba[:,:,3]
        else:
            mask_alpha = 1.0

        for i in xrange(1, self.dataset.RasterCount+1):
            band = self.dataset.GetRasterBand(i)
            interp = band.GetColorInterpretation()
            data = array[:,:,i-1] * mask_alpha

            if interp == gdal.GCI_RedBand:
                rgba[:,:,0] = data / 255.0
            elif interp == gdal.GCI_GreenBand:
                rgba[:,:,1] = data / 255.0
            elif interp == gdal.GCI_BlueBand:
                rgba[:,:,2] = data / 255.0
            elif interp == gdal.GCI_AlphaBand:
                rgba[:,:,3] = data / 255.0
            elif interp == gdal.GCI_GrayIndex:
                rgba[:,:,:3] = np.repeat(np.atleast_3d(data / 255.0), 3, 2)
            elif interp == gdal.GCI_PaletteIndex:
                table = band.GetColorTable()
                entries = np.array([tuple(table.GetColorEntry(i)) for i in xrange(table.GetCount())])

                # FIXME: This assumes the palette is RGBA
                rgba = np.float32(entries[np.int32(data)]) / 255.0
                for i in xrange(4):
                    rgba[:,:,i] *= mask_alpha

        return rgba

    def _render(self, envelope, size=None):
        if size is None:
            size = map(int, envelope.size())

        # check if the requested area is contained within the dataset bounds
        ds_boundary = self.boundary.transform_to(
                envelope.spatial_reference,
                min(self.envelope.size()) / max(size),
                min(envelope.size()) / max(size),
        )
        requested_boundary = core.boundary_from_envelope(envelope)
        if not ds_boundary.geometry.Intersects(requested_boundary.geometry):
            # early out if the dataset is nowhere near the requested envelope
            return ContentType.NONE, None

        # Get the destination raster
        raster = _gdal.create_render_dataset(
                envelope, size, prototype_ds=self.dataset)
        ds = raster.dataset

        desired_srs_wkt = envelope.spatial_reference.ExportToWkt()
        gdal.ReprojectImage(
                self.dataset, ds,
                self.dataset.GetProjection(),
                desired_srs_wkt,
                gdal.GRA_NearestNeighbour if self.is_palette else gdal.GRA_Bilinear)

        # Create a mask raster
        mask_raster = _gdal.create_render_dataset(envelope, size, data_type=gdal.GDT_Float32)
        mask_ds = mask_raster.dataset
        band = mask_ds.GetRasterBand(1)
        band.SetColorInterpretation(gdal.GCI_Undefined)
        band.SetNoDataValue(float('nan'))
        band.Fill(float('nan'))
        gdal.ReprojectImage(
                self.dataset, mask_ds,
                self.dataset.GetProjection(),
                desired_srs_wkt,
                gdal.GRA_NearestNeighbour)
        mask_band = mask_ds.GetRasterBand(1).GetMaskBand()

        return ContentType.RASTER, core.Raster.from_dataset(ds, mask_band=mask_band, to_rgba=self._to_rgba)

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

        to_rgba = core.RgbaFromBands(
            (
                (core.RgbaFromBands.RED,    1.0/255.0),
                (core.RgbaFromBands.GREEN,  1.0/255.0),
                (core.RgbaFromBands.BLUE,   1.0/255.0),
            ),
            True)

        if size[0] <= 256 and size[1] <= 256:
            pref_envelope = envelope.transform_to(
                    self.preferred_srs,
                    min(envelope.size()) / float(max(size)))
            zoom = self._zoom_for_envelope(pref_envelope, size)
            raster = self._render_tile(envelope, size, zoom)
            return ContentType.RASTER, core.Raster.from_dataset(raster.dataset, to_rgba=to_rgba)

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
        
        return ContentType.RASTER, core.Raster.from_dataset(raster.dataset, to_rgba=to_rgba)

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

                tile_raster = None
                gdal.Unlink('/vsimem/tmptile.png')

        return raster
