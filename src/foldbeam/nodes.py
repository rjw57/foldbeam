from __future__ import print_function

from . import _gdal, core, graph, pads, transform
from .graph import connect, ConstantNode, node
import copy
import math
from ModestMaps.Core import Point, Coordinate
from osgeo import gdal
from osgeo.osr import SpatialReference
import numpy as np
import StringIO
import TileStache

@node
class ToRgbaRasterNode(graph.Node):
    def __init__(self, input_pad):
        super(ToRgbaRasterNode, self).__init__()
        self.add_output('output', graph.RasterType, self._render)
        self.add_input('input', graph.RasterType)

    def _render(self, envelope, size):
        if size is None:
            size = map(int, envelope.size())

        raster = self.inputs.input(envelope, size)
        if raster is None:
            return None

        return core.Raster(raster.to_rgba(), envelope, to_rgba=lambda x: x)

@node
class LayerRasterNode(graph.Node):
    def __init__(self, top=None, bottom=None, top_opacity=None, bottom_opacity=None):
        super(LayerRasterNode, self).__init__()
        self.add_output('output', graph.RasterType, self._render)
        self.add_input('top', graph.RasterType, top)
        self.add_input('top_opacity', graph.FloatType, top_opacity if top_opacity is not None else 1)
        self.add_input('bottom', graph.RasterType, top)
        self.add_input('bottom_opacity', graph.FloatType, bottom_opacity if bottom_opacity is not None else 1)

    def _render(self, envelope, size):
        opacities = [
            self.inputs.bottom_opacity(),
            self.inputs.top_opacity(),
        ]

        layers = [
            self.inputs.bottom(envelope=envelope, size=size),
            self.inputs.top(envelope=envelope, size=size),
        ]

        output = None
        for raster, opacity in zip(layers, opacities):
            if raster is None:
                continue
            layer = raster.to_rgba()
            if layer is None:
                print('layer failed to convert')
                continue

            if output is None:
                output = layer
                output *= opacity
                continue

            one_minus_alpha = np.atleast_3d(1.0 - opacity * layer[:,:,3])
            
            output[:,:,:3] *= np.repeat(one_minus_alpha, 3, 2) 
            output[:,:,:3] += opacity * layer[:,:,:3]

            output[:,:,3] *= one_minus_alpha[:,:,0]
            output[:,:,3] += opacity * layer[:,:,3]

        if output is None:
            return None

        return core.Raster(output, envelope, to_rgba=lambda x: x)

@node
class FileReaderNode(graph.Node):
    def __init__(self, filename=None):
        super(FileReaderNode, self).__init__()
        self.contents = None
        self.add_input('filename', str, filename)
        self.add_output('contents', gdal.Dataset, self._load)

    def _load(self):
        if self.contents is not None:
            return self.contents

        filename = self.inputs.filename
        if filename is None:
            return None

        self.contents = open(filename).read()
        return self.contents

@node
class GDALDatasetSourceNode(graph.Node):
    def __init__(self, filename=None):
        super(GDALDatasetSourceNode, self).__init__()
        self.add_input('filename', str, filename)
        self.dataset = None
        self.add_output('dataset', gdal.Dataset, self._load)

    def _load(self):
        if self.dataset is not None:
            return self.dataset

        filename = self.inputs.filename()
        if filename is None:
            return None

        self.dataset = gdal.Open(filename)
        return self.dataset

@node
class GDALDatasetRasterNode(graph.Node):
    def __init__(self, dataset=None):
        super(GDALDatasetRasterNode, self).__init__()

        self.add_input('dataset', gdal.Dataset)
        if isinstance(dataset, basestring):
            ds_node = self.add_subnode(GDALDatasetSourceNode(dataset))
            connect(ds_node.outputs.dataset, self.inputs.dataset)
        elif dataset is not None:
            ds_node = self.add_subnode(ConstantNode(gdal.Dataset, dataset))
            connect(ds_node.outputs.dataset, self.inputs.dataset)

        self.add_output('output', graph.RasterType, self._render_reprojected)

    @property
    def dataset(self):
        return self.inputs.dataset()

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

    def _render_reprojected(self, **kwargs):
        self.spatial_reference = SpatialReference()
        self.spatial_reference.ImportFromWkt(self.dataset.GetProjection())
        self.envelope = _gdal.dataset_envelope(self.dataset, self.spatial_reference)
        self.boundary = core.boundary_from_envelope(self.envelope)
        self.is_palette = self.dataset.GetRasterBand(1).GetColorInterpretation() == gdal.GCI_PaletteIndex

        return pads.ReprojectingRasterFilter(
                self.spatial_reference,
                pads.TiledRasterFilter(self._render, tile_size=256))(**kwargs)

    def _render(self, envelope, size):
        if self.dataset is None:
            return None

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

@node
class TileStacheNode(graph.Node):
    def __init__(self, config_file=None):
        super(TileStacheNode, self).__init__()

        self.add_input('config_file', str, config_file)

        filename = self.inputs.config_file()
        self.config = None
        if filename is not None:
            self.config = TileStache.parseConfigfile(filename)
            for name in sorted(self.config.layers.keys()):
                self.add_output(name, TileStache.Core.Layer, self._layer_function(name))

    def _layer_function(self, name):
        return lambda: self.config.layers[name]

@node
class TileStacheRasterNode(graph.Node):
    @property
    def layer(self):
        return self.inputs.layer()

    def __init__(self, layer=None):
        super(TileStacheRasterNode, self).__init__()

        self.add_input('layer', TileStache.Core.Layer, layer)
        self.add_output('output', graph.RasterType, pads.TiledRasterFilter(self._render, tile_size=256))

    def _update(self):
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

    def _render(self, envelope, size):
        if self.layer is None:
            return None

        if size is None:
            size = [int(x) for x in envelope.size()]

        # FIXME: Once output hints are enabled, they should be used here
        self._update()
        try:
            pref_envelope = envelope.transform_to(
                    self.preferred_srs,
                    min(envelope.size()) / float(max(size)))
        except core.ProjectionError:
            # Skip projection errors
            return None

        zoom = self._zoom_for_envelope(pref_envelope, size)

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

        tile_rasters = []

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

                tile_rasters.append(core.Raster.from_dataset(tile_raster))

                tile_raster = None
                gdal.Unlink('/vsimem/tmptile.png')

        output = core.Raster(
            np.ma.masked_all((size[1], size[0], 4), dtype=np.float32),
            envelope,
            to_rgba=core.RgbaFromBands(
            (
                (core.RgbaFromBands.RED,    1.0/255.0),
                (core.RgbaFromBands.GREEN,  1.0/255.0),
                (core.RgbaFromBands.BLUE,   1.0/255.0),
                (core.RgbaFromBands.ALPHA,  1.0/255.0),
            ), False)
        )
        transform.reproject_rasters(output, tile_rasters)
        return output
