"""
Handling raster data
====================

"""
from __future__ import print_function

import logging
import math
import os

from ModestMaps.Core import Point, Coordinate
import numpy as np
from osgeo import gdal, gdal_array, osr
import pyproj
import TileStache

from foldbeam import _gdal, core, graph

class Raster(object):
    """An array of pixels associated with a rectangle in some geographic projection. A raster is a wrapper around a
    :py:class:`numpy.array` instance which can be accessed directly via the :py:attr:`array` attribute. A raster has an
    associated envelope and the left, right, top and bottom edges of the array are mapped to the left, right, top and
    bottom of the envelope.

    :param array: the initial contents of the raster
    :type array: :py:class:`numpy.array` or similar
    :param envelope: the bounding box and associated projection which encloses this raster
    :type envelope: :py:class:`core.Envelope`
    :param to_rgba: called with :py:attr:`array` to convert this raster into a 4-channel RGBA raster
    :type to_rgba: callable
    :param can_interpolate: flag indicating whether interpolation of values in this raster is valid
    :param prototype: copy *can_interpolate* and *to_rgba* from a prototype :py:class:`Raster`
    :type prototype: :py:class:`Raster`

    """

    def __init__(self, array, envelope, to_rgba=None, can_interpolate=True, prototype=None):
        self.array = np.atleast_3d(np.float32(array))
        self.envelope = envelope
        if to_rgba is None:
            to_rgba = to_rgba_unknown
        self.to_rgba_cb = to_rgba
        self.can_interpolate = can_interpolate

        if prototype is not None:
            self.to_rgba_cb = prototype.to_rgba_cb
            self.can_interpolate = prototype.can_interpolate

    def to_rgba(self):
        """Obtain an array with shape (height, width, 4) where the depth are respectively the red, green, blue and alpha
        values for displaying this raster on the interval [0,1).

        """
        return self.to_rgba_cb(self.array)

    def as_rgba_dataset(self):
        """Obtain a :py:class:`gdal.Dataset` with red, green, blue and alpha bands representing the array returned from
        :py:meth:`to_rgba`.

        """
        arr = self.to_rgba()
        if len(arr.shape) > 2:
            arr = arr.transpose((2,0,1))
        ds = gdal_array.OpenArray(np.uint8(255.0*np.clip(arr,0,1)))
        ds.SetProjection(self.envelope.spatial_reference.ExportToWkt())
        size = [ds.RasterXSize, ds.RasterYSize]
        xscale, yscale = [float(x[0])/float(x[1]) for x in zip(self.envelope.offset(), size)]
        ds.SetGeoTransform((self.envelope.left, xscale, 0, self.envelope.top, 0, yscale))

        return ds

    def as_dataset(self):
        """Obtain a version of this raster as a :py:class:`gdal.Dataset`."""

        arr = self.array
        if len(arr.shape) > 2:
            arr = arr.transpose((2,0,1))

        ds = gdal_array.OpenArray(arr)

        ds.SetProjection(self.envelope.spatial_reference.ExportToWkt())
        size = [ds.RasterXSize, ds.RasterYSize]
        xscale, yscale = [float(x[0])/float(x[1]) for x in zip(self.envelope.offset(), size)]
        ds.SetGeoTransform((self.envelope.left, xscale, 0, self.envelope.top, 0, yscale))

        mask = np.ma.getmask(self.array)
        mask_ds = None
        if mask is not np.ma.nomask:
            # There is some mask we need to overlay onto the dataset
            for i in xrange(1, ds.RasterCount+1):
                band = ds.GetRasterBand(i)
                band.SetNoDataValue(float('nan'))
                band.WriteArray(np.where(mask[:,:,i-1], float('nan'), self.array[:,:,i-1]))

        return ds

    def write_tiff(self, filename):
        """Write this raster to a GeoTIFF."""
        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy(filename, self.as_rgba_dataset())

    @classmethod
    def from_dataset(cls, ds, mask_band=None, **kwargs):
        """Create a :py:class:`Raster` from a :py:class:`gdal.Dataset`.

        Extra keyword arguments are passed to the :py:class:`Raster` constructor.

        """
        ds_array = ds.ReadAsArray()
        if len(ds_array.shape) > 2:
            ds_array = ds_array.transpose((1,2,0))
        else:
            ds_array = np.atleast_3d(ds_array)

        if mask_band is not None:
            mask = np.atleast_3d(mask_band.ReadAsArray()) == 0
            if np.any(mask):
                ds_array = np.ma.masked_where(np.repeat(mask, ds_array.shape[2], 2), ds_array)

        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjection())
        envelope = dataset_envelope(ds, srs)
        
        can_interpolate = gdal.GCI_PaletteIndex not in [
            ds.GetRasterBand(i).GetColorInterpretation()
            for i in xrange(1, ds.RasterCount+1)
        ]
        if 'can_interpolate' in kwargs:
            can_interpolate = can_interpolate and kwargs['can_interpolate']
            del kwargs['can_interpolate']

        return Raster(ds_array, envelope, can_interpolate=can_interpolate, **kwargs)

def to_rgba_unknown(array):
    """Default conversion from an array of unknown type to an RGBA array. This simply fills the array with a default
    pattern.

    """

    array = np.atleast_2d(array)
    rgba = np.empty(array.shape[:2] + (4,))
    red = np.reshape(np.arange(array.shape[1], dtype=np.float32) / array.shape[1], (1, array.shape[1]))
    green = np.reshape(np.arange(array.shape[0], dtype=np.float32) / array.shape[0], (array.shape[0], 1))
    alpha = 1
    mask = np.ma.getmask(array)
    if mask is not np.ma.nomask:
        alpha = np.where(np.any(mask, 2), 0.0, 1.0)
    rgba[:, :, 0] = np.repeat(red, array.shape[0], 0) * alpha
    rgba[:, :, 1] = np.repeat(green, array.shape[1], 1) * alpha
    rgba[:, :, 2] = 0
    rgba[:, :, 3] = alpha
    return rgba

class RgbaFromBands(object):
    # Band interpretations
    RED         = 'RED'
    GREEN       = 'GREEN'
    BLUE        = 'BLUE'
    ALPHA       = 'ALPHA'
    GRAY        = 'GRAY'
    NONE        = 'NONE'

    def __init__(self, bands, is_premultiplied):
        self.bands = bands
        self.is_premultiplied = is_premultiplied

    def __call__(self, array):
        rgba = to_rgba_unknown(array)
        if np.any(rgba[:,:,3] != 1.0):
            mask_alpha = rgba[:,:,3]
        else:
            mask_alpha = 1.0

        for idx, band in enumerate(self.bands):
            scale = (band[1] if len(band) >= 2 else 1.0) * mask_alpha
            interp = band[0]

            if interp is RgbaFromBands.GRAY:
                rgba[:, :, :3] = np.repeat(array[:,:,idx], 3, 2) * scale
            elif interp is RgbaFromBands.RED:
                rgba[:, :, 0] = array[:,:,idx]
                rgba[:, :, 0] *= scale
            elif interp is RgbaFromBands.GREEN:
                rgba[:, :, 1] = array[:,:,idx]
                rgba[:, :, 1] *= scale
            elif interp is RgbaFromBands.BLUE:
                rgba[:, :, 2] = array[:,:,idx]
                rgba[:, :, 2] *= scale
            elif interp is RgbaFromBands.ALPHA:
                rgba[:, :, 3] = array[:,:,idx]
                rgba[:, :, 3] *= scale

        if not self.is_premultiplied:
            for i in xrange(3):
                rgba[:, :, i] *= rgba[:,:,3]

        return rgba

def dataset_envelope(dataset, spatial_reference):
    gt = dataset.GetGeoTransform()
    geo_trans = np.matrix([
        [ gt[1], gt[2], gt[0] ],
        [ gt[4], gt[5], gt[3] ],
    ])

    bounds = geo_trans * np.matrix([
        [ 0, 0, 1],
        [ 0, dataset.RasterYSize, 1 ],
        [ dataset.RasterXSize, 0, 1],
        [ dataset.RasterXSize, dataset.RasterYSize, 1 ],
    ]).transpose()

    min_bound = bounds.min(1)
    max_bound = bounds.max(1)

    return core.Envelope(
        bounds[0,0], bounds[0,3],
        bounds[1,0], bounds[1,3],
        spatial_reference
    )

def compute_warp(dst_envelope, dst_size, src_spatial_reference):
    """Compute the projection co-ordinates in a source spatial projection for pixels in a destination image.

    :param dst_envelope: the envelope of the destination raster
    :type dst_envelope: :py:class:`core.Envelope`
    :param dst_size: the width and height of the destination raster
    :type dst_size: pair of integer
    :param src_spatial_reference: co-ordinate system of the source raster
    :type src_spatial_reference: :py:class:`osgeo.osr.SpatialReference`
    :rtype: pair of arrays

    Compute the projection co-ordinates of each pixel in a destination raster when projected into the source spatial
    reference. This is necessary to re-project images correctly.

    The return value is a pair of array-like objects giving the x and y co-ordinates. The returned arrays are the width
    and height specified in dst_size.

    """

    # Compute x- and y-co-ordinates in dst from the envelope
    dst_cols, dst_rows = dst_size
    dst_x = np.repeat(
            np.linspace(dst_envelope.left, dst_envelope.right, dst_cols).reshape(1, dst_cols),
            dst_rows, 0)
    dst_y = np.repeat(
            np.linspace(dst_envelope.top, dst_envelope.bottom, dst_rows).reshape(dst_rows, 1),
            dst_cols, 1)

    assert dst_x.shape == (dst_rows, dst_cols)
    assert dst_y.shape == (dst_rows, dst_cols)

    # Special case when source and destination have same srs
    if dst_envelope.spatial_reference.IsSame(src_spatial_reference):
        return dst_x, dst_y

    dst_proj = pyproj.Proj(dst_envelope.spatial_reference.ExportToProj4())
    src_proj = pyproj.Proj(src_spatial_reference.ExportToProj4())

    src_x, src_y = pyproj.transform(dst_proj, src_proj, dst_x, dst_y)

    return src_x, src_y

def proj_to_pixels(x, y, envelope, size):
    """Compute pixel co-ordinates of projection co-ordinates x and y in image with envelope and size specified."""

    off = envelope.offset()
    x = (x - envelope.left) * (float(size[0]-1) / off[0])
    y = (y - envelope.top) * (float(size[1]-1) / off[1])
    return x,y

def pixels_to_proj(x, y, envelope, size):
    """Compute projection co-ordinates of pixel co-ordinates x and y in image with envelope and size specified."""

    off = envelope.offset()
    x = x * (off[0] / float(size[0]-1)) + envelope.left
    y = y * (off[1] / float(size[1]-1)) + envelope.right
    return x,y

def sample_raster(src_pixel_x, src_pixel_y, src_raster):
    """Sample pixels from a raster.

    :param src_pixel_x: array of pixel x-co-ordinates
    :param src_pixel_y: array of pixel y-co-ordinates
    :param src_raster: source raster
    :type src_raster: :py:class:`Raster`
    :rtype: :py:class:`numpy.array` or :py:class:`numpy.ma.array`

    The returned array has the same shape as src_raster with each value corresponding to the sampled value. The arrays
    src_pixel_x and src_pixel_y must have the same width and height as src_raster. If pixel co-ordinates outside of the
    range of those present in src_raster are specified, the values will be masked out of the resulting array and a numpy
    masked array will be returned.

    """

    px = np.int32(np.round(src_pixel_x))
    py = np.int32(np.round(src_pixel_y))

    x_valid = np.logical_and(px >= 0, px < src_raster.array.shape[1])
    y_valid = np.logical_and(py >= 0, py < src_raster.array.shape[0])
    valid = np.logical_and(x_valid, y_valid)

    valid_flag = valid.ravel()
    valid_src_indices = np.ravel_multi_index(
        (py.ravel()[valid_flag], px.ravel()[valid_flag]),
        src_raster.array.shape[:2]
    )

    dst_shape = np.atleast_2d(src_pixel_x).shape[:2] + (src_raster.array.shape[2],)
    dst = np.empty(shape=dst_shape, dtype=np.float32)

    for i in xrange(dst_shape[2]):
        dst[valid, i] = src_raster.array[:,:,i].ravel()[valid_src_indices]

    dst = np.ma.fix_invalid(
        dst,
        fill_value=np.nan,
        mask=np.repeat(np.atleast_3d(np.logical_not(valid)), dst_shape[2], 2)
    )

    return dst

def reproject_raster(dst, src):
    """Re-project a source raster into a destination raster.

    See :py:func:`reproject_rasters`.

    """
    reproject_rasters(dst, (src,))

def _py_reproject_rasters(dst, srcs):
    if len(srcs) == 0:
        return

    src_srs = srcs[0].envelope.spatial_reference
    assert all([x.envelope.spatial_reference.IsSame(src_srs) for x in srcs[1:]])

    dst_height, dst_width = dst.array.shape[:2]
    src_x, src_y = compute_warp(dst.envelope, (dst_width, dst_height), src_srs)
    for src in srcs:
        src_height, src_width = src.array.shape[:2]

        # Compute warp
        src_px, src_py = proj_to_pixels(src_x, src_y, src.envelope, (src_width, src_height))
        sample = sample_raster(src_px, src_py, src)

        bands = min(sample.shape[2], dst.array.shape[2])
        dst.array[:,:,:bands] = np.ma.filled(sample[:,:,:bands], dst.array[:,:,:bands])

def _gdal_reproject_rasters(dst, srcs):
    if len(srcs) == 0:
        return

    src_srs = srcs[0].envelope.spatial_reference
    assert all([x.envelope.spatial_reference.IsSame(src_srs) for x in srcs[1:]])

    mem_driver = gdal.GetDriverByName('MEM')
    dst_ds = mem_driver.CreateCopy('', dst.as_dataset())
    src_wkt = src_srs.ExportToWkt()
    dst_wkt = dst.envelope.spatial_reference.ExportToWkt()
    for src in srcs:
        gdal.ReprojectImage(
            src.as_dataset(), dst_ds,
            src_wkt, dst_wkt,
            gdal.GRA_Bilinear if src.can_interpolate else gdal.GRA_NearestNeighbour)

    dst.array = Raster.from_dataset(dst_ds).array

if 'FOLDBEAM_REPROJECTION_PROVIDER' in os.environ:
    _provider = os.environ['FOLDBEAM_REPROJECTION_PROVIDER']
    if _provider == 'GDAL':
        reproject_rasters = _gdal_reproject_rasters
    elif _provider == 'PROJ':
        reproject_rasters = _py_reproject_rasters
    else:
        raise ValueError('Unknown projection provider: ' + _provider)
else:
    reproject_rasters = _gdal_reproject_rasters

@graph.node
class CompositeOver(graph.Node):
    def __init__(self, top=None, bottom=None, top_opacity=None, bottom_opacity=None):
        super(CompositeOver, self).__init__()
        self.add_output('output', Raster, self._render)
        self.add_input('top', Raster, top)
        self.add_input('top_opacity', graph.FloatType, top_opacity)
        self.add_input('bottom', Raster, top)
        self.add_input('bottom_opacity', graph.FloatType, bottom_opacity)

        for input_pad in self.inputs.values():
            input_pad.damaged.connect(self._inputs_damaged)
            input_pad.connected.connect(self._inputs_damaged)

    def _inputs_damaged(self, boundary):
        self.outputs.output.damaged(boundary)

    def _render(self, envelope, size):
        opacities = [x if x is not None else 1.0 for x in [self.bottom_opacity, self.top_opacity]]
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

        return Raster(output, envelope, to_rgba=lambda x: x)

@graph.node
class GDALDatasetSourceNode(graph.Node):
    def __init__(self, filename=None):
        super(GDALDatasetSourceNode, self).__init__()
        self._dataset = None
        self._filename = None

        self.add_input('filename', str, filename)
        self.add_output('dataset', gdal.Dataset, lambda: self._dataset)

        self.inputs.filename.damaged.connect(self._filename_damaged)
        self.inputs.filename.connected.connect(self._filename_damaged)
        self._filename_damaged(None)

    def _filename_damaged(self, boundary, **kwargs):
        filename = self.inputs.filename()
        if filename == self._filename:
            return

        if filename is not None:
            logging.info('Opening GDAL dataset: ' + str(filename))
            self._dataset = gdal.Open(filename)
            logging.info('Opened GDAL dataset ' + str(self._dataset))
        else:
            logging.info('Dropping GDAL dataset ' + str(self._dataset))
            self._dataset = None

        self._filename = filename

@graph.node
class GDALDatasetRasterNode(graph.Node):
    def __init__(self, dataset=None):
        super(GDALDatasetRasterNode, self).__init__()

        self.add_input('dataset', gdal.Dataset)
        if isinstance(dataset, basestring):
            ds_node = self.add_subnode(GDALDatasetSourceNode(dataset))
            graph.connect(ds_node.outputs.dataset, self.inputs.dataset)
        elif dataset is not None:
            ds_node = self.add_subnode(graph.ConstantNode(gdal.Dataset, dataset))
            graph.connect(ds_node.outputs.dataset, self.inputs.dataset)

        self.add_output('output', Raster, self._render_reprojected)

    def _to_rgba(self, array):
        rgba = to_rgba_unknown(array)
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
        if self.dataset is None:
            return None

        self.spatial_reference = osr.SpatialReference()
        self.spatial_reference.ImportFromWkt(self.dataset.GetProjection())
        self.envelope = dataset_envelope(self.dataset, self.spatial_reference)
        self.boundary = core.boundary_from_envelope(self.envelope)
        self.is_palette = self.dataset.GetRasterBand(1).GetColorInterpretation() == gdal.GCI_PaletteIndex

        return ReprojectingRasterFilter(
                self.spatial_reference,
                TiledRasterFilter(self._render, tile_size=256))(**kwargs)

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

        return Raster.from_dataset(ds, mask_band=mask_band, to_rgba=self._to_rgba)

@graph.node
class TileStacheSource(graph.Node):
    def __init__(self, config_file=None, config=None):
        super(TileStacheSource, self).__init__()
        self.add_input('config_file', str, config_file)
        self._config = None
        self.inputs.config_file.damaged.connect(self._config_updated)
        self.inputs.config_file.connected.connect(self._config_updated)
        self._config_updated()

        if config is not None:
            self.config = config

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        self._update_pads_from_config()

    def _config_updated(self, *args, **kwargs):
        filename = self.config_file
        self.config = None
        if filename is not None:
            self.config = TileStache.parseConfigfile(filename)

    def _update_pads_from_config(self):
        if self.config is None:
            return
        for name in sorted(self.config.layers.keys()):
            self.add_output(name, Raster, self._layer_function(name))

    def _layer_function(self, name):
        return lambda **kwargs: self._render(layer=self.config.layers[name], **kwargs)

    def _zoom_for_envelope(self, layer, envelope, size):
        # How many tiles should cover each axis
        n_tiles = map(lambda x: x/256.0, size)

        # Over what range?
        envelope_size = map(abs, envelope.offset())
        proj_range = min(envelope_size)

        # Calculate the bounds of the zoom level 0 tile
        bounds = [
            layer.projection.coordinateProj(Coordinate(0,0,0)),
            layer.projection.coordinateProj(Coordinate(1,1,0)),
        ]
        proj_axes = (bounds[1].x - bounds[0].x, bounds[1].y - bounds[0].y)
        proj_size = map(abs, proj_axes)

        # Giving a rough tile size in projection coordinate of...
        zoomed_tile_size = map(lambda x: x[0]/x[1], zip(envelope_size, n_tiles))
    
        # And convert to a zoom
        zooms = map(lambda x: math.log(x[0], 2) - math.log(x[1], 2), zip(proj_size, zoomed_tile_size))

        # Which is closer to the precise zoom we want?
        zoom = max(zooms)
        floor_diff = abs(math.pow(2, zoom) - math.pow(2, math.floor(zoom)))
        ceil_diff = abs(math.pow(2, zoom) - math.pow(2, math.ceil(zoom)))

        # Choose an overall zoom from these
        int_zoom = int(math.ceil(zoom)) if ceil_diff < floor_diff else int(math.floor(zoom))
        return max(0, min(18, int_zoom))

    def _render(self, layer=None, envelope=None, size=None):
        if layer is None or envelope is None:
            return None

        if size is None:
            size = [int(x) for x in envelope.size()]

        preferred_srs = osr.SpatialReference()
        preferred_srs.ImportFromProj4(layer.projection.srs)
        preferred_srs_wkt = preferred_srs.ExportToWkt()

        # FIXME: Once output hints are enabled, they should be used here
        try:
            pref_envelope = envelope.transform_to(
                    preferred_srs,
                    min(envelope.size()) / float(max(size)))
        except core.ProjectionError:
            # Skip projection errors
            return None

        # Calculate the zoom factor appropriate for this envelope
        zoom = self._zoom_for_envelope(layer, pref_envelope, size)

        # Get the destination raster
        raster = _gdal.create_render_dataset(envelope, size, 4)
        assert tuple(size) == (raster.dataset.RasterXSize, raster.dataset.RasterYSize)

        # How many tiles overall in x and y at this zoom
        n_proj_tiles = math.pow(2, zoom)

        # Compute the tile co-ordinates of each corner
        corners = [
                layer.projection.projCoordinate(Point(pref_envelope.left, pref_envelope.top)),
                layer.projection.projCoordinate(Point(pref_envelope.right, pref_envelope.top)),
                layer.projection.projCoordinate(Point(pref_envelope.left, pref_envelope.bottom)),
                layer.projection.projCoordinate(Point(pref_envelope.right, pref_envelope.bottom)),
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
                tile_tl_point = layer.projection.coordinateProj(Coordinate(r,c,zoom))
                tile_br_point = layer.projection.coordinateProj(Coordinate(r+1,c+1,zoom))

                c = c % n_proj_tiles
                if c < 0:
                    c += n_proj_tiles
                tile_coord = Coordinate(r, c, zoom)

                try:
                    tile_type, png_data = TileStache.getTile(layer, tile_coord, 'png')
                    if tile_type != 'image/png':
                        print('Did not get PNG data when fetching tile %s. Skipping.' % (tile_coord))
                        continue
                except IOError as e:
                    print('Ignoring error fetching tile %s (%s).' % (tile_coord, e))
                    continue

                gdal.FileFromMemBuffer('/vsimem/tmptile.png', png_data)
                tile_raster = gdal.Open('/vsimem/tmptile.png')
                tile_raster.SetProjection(preferred_srs_wkt)

                xscale = (tile_br_point.x - tile_tl_point.x) / tile_raster.RasterXSize
                yscale = (tile_br_point.y - tile_tl_point.y) / tile_raster.RasterXSize
                tile_raster.SetGeoTransform((
                    tile_tl_point.x, xscale, 0.0,
                    tile_tl_point.y, 0.0, yscale,
                ))

                tile_rasters.append(Raster.from_dataset(tile_raster))

                tile_raster = None
                gdal.Unlink('/vsimem/tmptile.png')

        output = Raster(
            np.ma.masked_all((size[1], size[0], 4), dtype=np.float32),
            envelope,
            to_rgba=RgbaFromBands(
            (
                (RgbaFromBands.RED,    1.0/255.0),
                (RgbaFromBands.GREEN,  1.0/255.0),
                (RgbaFromBands.BLUE,   1.0/255.0),
                (RgbaFromBands.ALPHA,  1.0/255.0),
            ), False)
        )
        reproject_rasters(output, tile_rasters)

        return output

class TiledRasterFilter(object):
    def __init__(self, render_cb, tile_size=None):
        self.render_cb = render_cb
        self.tile_size = tile_size

    def __call__(self, envelope=None, size=None, **kwargs):
        if envelope is None:
            return None

        if size is None:
            size = map(int, envelope.size())

        if self.tile_size is None:
            raster = self.render_cb(envelope=envelope, size=size, **kwargs)
            if raster is None or len(raster) == 0 or raster[0] is None:
                return None
            return raster[0]

        tiles = []
        tile_offsets = []
        xscale, yscale = [x[0] / float(x[1]) for x in zip(envelope.offset(), size)]
        for x in xrange(0, size[0], self.tile_size):
            width = min(x + self.tile_size, size[0]) - x
            for y in xrange(0, size[1], self.tile_size):
                height = min(y + self.tile_size, size[1]) - y
                tile_envelope = core.Envelope(
                        envelope.left + xscale * x,
                        envelope.left + xscale * (x + width),
                        envelope.top + yscale * y,
                        envelope.top + yscale * (y + height),
                        envelope.spatial_reference,
                )
                tiles.append(self.render_cb(envelope=tile_envelope, size=(width, height), **kwargs))
                tile_offsets.append((x,y))

        results = [x for x in zip(tile_offsets, tiles) if x[1] is not None]
        if len(results) == 0:
            return None

        # FIXME: This assumes that to_rgba_cb is the same for each tile
        prototype = results[0][1]
        depth = prototype.array.shape[2]

        shape = (size[1], size[0])
        mask = np.ones(shape + (depth,), dtype=np.bool)
        data = np.zeros(shape + (depth,), dtype=np.float32)
        for pos, tile in results:
            x, y = pos
            h, w = tile.array.shape[:2]

            tile_mask = np.ma.getmask(tile.array)
            if tile_mask is np.ma.nomask:
                tile_mask = False

            mask[y:(y+h), x:(x+w), :] = tile_mask
            data[y:(y+h), x:(x+w), :] = tile.array

        if np.any(mask):
            data = np.ma.array(data, mask=mask)

        return Raster(data, envelope, prototype=prototype)

class ReprojectingRasterFilter(object):
    def __init__(self, native_spatial_reference, render_cb):
        self.native_spatial_reference = native_spatial_reference
        self.native_spatial_reference_wkt = native_spatial_reference.ExportToWkt()
        self.render_cb = render_cb

    def __call__(self, envelope=None, size=None, **kwargs):
        if envelope is None:
            return None

        if size is None:
            size = map(int, envelope.size())

        if envelope.spatial_reference.IsSame(self.native_spatial_reference):
            return self.render_cb(envelope=envelope, size=size, **kwargs)

        # We need to reproject this data. Convert the envelope into the native spatial reference
        try:
            native_envelope = envelope.transform_to(
                    self.native_spatial_reference,
                    min(envelope.size()) / float(max(size)))
        except ProjectionError:
            # If we fail to reproject, return a null tile
            return None

        # Get the native tile
        raster = self.render_cb(envelope=native_envelope, size=size, **kwargs)
        if raster is None:
            return None

        raster_ds = raster.as_dataset()

        # Get the destination raster
        ds = _gdal.create_render_dataset(envelope, size, 4).dataset

        desired_srs_wkt = envelope.spatial_reference.ExportToWkt()
        gdal.ReprojectImage(
                raster_ds, ds,
                self.native_spatial_reference_wkt,
                desired_srs_wkt,
                gdal.GRA_Bilinear if raster.can_interpolate else gdal.GRA_NearestNeighbour)

        # Create a mask raster
        mask_raster = _gdal.create_render_dataset(envelope, size, 1, data_type=gdal.GDT_Float32)
        mask_ds = mask_raster.dataset
        band = mask_ds.GetRasterBand(1)
        band.SetColorInterpretation(gdal.GCI_Undefined)
        band.SetNoDataValue(float('nan'))
        band.Fill(float('nan'))
        gdal.ReprojectImage(
                raster_ds, mask_ds,
                self.native_spatial_reference_wkt,
                desired_srs_wkt,
                gdal.GRA_NearestNeighbour)
        mask_band = mask_ds.GetRasterBand(1).GetMaskBand()

        return Raster.from_dataset(ds, mask_band=mask_band, prototype=raster)
