import _gdal
import core
import graph
import math
from ModestMaps.Core import Point, Coordinate
from osgeo import gdal
from osgeo.osr import SpatialReference
import pads as pads_
import numpy as np
import StringIO
import TileStache

class ToRgbaRasterNode(graph.Node):
    def __init__(self, input_pad):
        super(ToRgbaRasterNode, self).__init__()
        self.output = pads_.CallableOutputPad(cb=self._render, type=pads.ContentType.RASTER)
        self.input_pad = input_pad

    def _render(self, envelope, size):
        if size is None:
            size = map(int, envelope.size())

        resp = self.input_pad.pull(envelope, size)
        if resp is None:
            return pads_.ContentType.NONE, None

        type_, raster = resp
        if type_ is pads_.ContentType.NONE:
            return pads_.ContentType.NONE, None

        if type_ is not pads_.ContentType.RASTER:
            print('Skipping invalid raster')
            return pads_.ContentType.NONE, None

        return pads_.ContentType.RASTER, core.Raster(raster.to_rgba(), envelope, to_rgba=lambda x: x)

class LayerRasterNode(graph.Node):
    class _GrowingList(list):
        def __setitem__(self, index, value):
            if index >= len(self):
                self.extend([None]*(index + 1 - len(self)))
                list.__setitem__(self, index, value)

    def __init__(self, layers=None, opacities=None):
        super(LayerRasterNode, self).__init__()
        self.output = pads_.TiledRasterOutputPad(self._render)
        self.layers = LayerRasterNode._GrowingList()

        if layers is not None:
            self.layers.extend(layers)

        self.opacities = opacities

    def _render(self, tiles):
        rv = []
        for envelope, size in tiles:
            rv.append(self._render_tile(envelope, size))
        return rv

    def _render_tile(self, envelope, size):
        if len(self.layers) == 0:
            return None

        if self.opacities is None:
            opacities = (1,) * len(self.layers)
        else:
            opacities = self.opacities

        if len(opacities) != len(self.layers):
            raise ValueError('opacities: expected sequence of length %s' % (len(self.layers),))

        output = None
        for response, opacity in zip([pad(envelope, size) for pad in self.layers], opacities):
            if response is None:
                continue

            type_, raster = response

            if type_ == pads_.ContentType.NONE:
                continue

            if type_ is not pads_.ContentType.RASTER:
                raise RuntimeError('Input is not raster')
            
            layer = raster.to_rgba()
            if layer is None:
                print('layer failed to convert')
                continue

            if output is None:
                output = layer
                continue

            one_minus_alpha = np.atleast_3d(1.0 - opacity * layer[:,:,3])
            
            output[:,:,:3] *= np.repeat(one_minus_alpha, 3, 2) 
            output[:,:,:3] += opacity * layer[:,:,:3]

            output[:,:,3] *= one_minus_alpha[:,:,0]
            output[:,:,3] += opacity * layer[:,:,3]

        if output is None:
            return None

        return core.Raster(output, envelope, to_rgba=lambda x: x)

class GDALDatasetRasterNode(graph.Node):
    def __init__(self, dataset):
        super(GDALDatasetRasterNode, self).__init__()

        if isinstance(dataset, basestring):
            self.dataset = gdal.Open(dataset)
        else:
            self.dataset = dataset

        self.spatial_reference = SpatialReference()
        self.spatial_reference.ImportFromWkt(self.dataset.GetProjection())

        source_pad = pads_.TiledRasterOutputPad(self._render, tile_size=256)
        self.output = pads_.ReprojectingOutputPad(self.spatial_reference, source_pad)

        self.envelope = _gdal.dataset_envelope(self.dataset, self.spatial_reference)
        self.boundary = core.boundary_from_envelope(self.envelope)
        self.is_palette = self.dataset.GetRasterBand(1).GetColorInterpretation() == gdal.GCI_PaletteIndex

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

    def _render(self, tiles):
        rv = []
        for envelope, size in tiles:
            rv.append(self._render_tile(envelope, size))
        return rv

    def _render_tile(self, envelope, size):
        assert envelope.spatial_reference.IsSame(self.spatial_reference)

        # check if the requested area is contained within the dataset bounds
        requested_boundary = core.boundary_from_envelope(envelope)
        if not self.boundary.geometry.Intersects(requested_boundary.geometry):
            # early out if the dataset is nowhere near the requested envelope
            return None

        # Get the destination raster
        raster = _gdal.create_render_dataset(envelope, size, prototype_ds=self.dataset)
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

        return core.Raster.from_dataset(ds, mask_band=mask_band, to_rgba=self._to_rgba)

class TileStacheRasterNode(graph.Node):
    def __init__(self, layer=None, config=None):
        super(TileStacheRasterNode, self).__init__()
        self.output = pads_.TiledRasterOutputPad(self._render, tile_size=256)

        if isinstance(layer, basestring):
            if config is None:
                raise ValueError('config must not be None')
            self.config = TileStache.parseConfigfile(config)
            self.layer = self.config.layers[layer]
        else:
            self.layer = layer
            self.config = layer.config

        self.preferred_srs = SpatialReference()
        self.preferred_srs.ImportFromProj4(self.layer.projection.srs)
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

    def _render(self, tiles):
        rv = []

        zooms = []
        for envelope, size in tiles:
            try:
                pref_envelope = envelope.transform_to(
                        self.preferred_srs,
                        min(envelope.size()) / float(max(size)))
            except core.ProjectionError:
                # Skip projection errors
                continue
            zooms.append(self._zoom_for_envelope(pref_envelope, size))
        
        # Choose the 75th percentile zoom
        zooms.sort()
        zoom = zooms[(len(zooms)>>1) + (len(zooms)>>2)]

        for envelope, size in tiles:
            rv.append(self._render_tile(envelope, size, zoom))
        return rv

    def _render_tile(self, envelope, size, zoom):
        # Get the destination raster
        raster = _gdal.create_render_dataset(envelope, size, 4)
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

        return core.Raster.from_dataset(raster.dataset, to_rgba=core.RgbaFromBands(
            (
                (core.RgbaFromBands.RED,    1.0/255.0),
                (core.RgbaFromBands.GREEN,  1.0/255.0),
                (core.RgbaFromBands.BLUE,   1.0/255.0),
                (core.RgbaFromBands.ALPHA,  1.0/255.0),
            ),
            False))
