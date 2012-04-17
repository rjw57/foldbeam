from core import Envelope
from osgeo import gdal, ogr

_counter = 0
_driver = gdal.GetDriverByName('GTiff')

class _DatasetWrapper(object):
    def __init__(self, dataset, filename):
        self.dataset = dataset
        self.filename = filename

    def __del__(self):
        if self.filename is not None:
            gdal.Unlink(self.filename)

def create_render_dataset(envelope, envelope_srs, size=None, band_count=3, data_type=gdal.GDT_Byte):
    global _counter, _driver

    if size is None:
        size = [abs(x) for x in envelope[2:]]

    _counter += 1
    name = '/vsimem/tmp/raster_%07d.tiff' % _counter
    raster = _driver.Create(name, size[0], size[1], band_count, data_type)

    # Set the dataset projection and geo transform
    raster.SetProjection(envelope_srs.ExportToWkt())
    xscale, yscale = [float(x[0])/float(x[1]) for x in zip(envelope.offset(), size)]
    raster.SetGeoTransform((envelope.left, xscale, 0, envelope.top, 0, yscale))

    return _DatasetWrapper(raster, name)

class ProjectionError(Exception):
    def __init__(self, message):
        self.message = message

def transform_envelope(envelope, src_srs, dst_srs, segment_length=None):
    """envelope is a core.Envelope instance giving the (left, right, top, bottom) of an envelope in the src_srs
    ogr.SpatialReference.  Return the corresponding envelope in the dts_srs ogr.SpatialReference.

    If segment_length is not None it is the maximum length *in the source SRS* to segment the boundary by.

    """

    # Test for identity transform
    if src_srs.IsSame(dst_srs):
        return envelope

    gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', 'TRUE')

    # Create polygon representing envelope
    bound_geom = ogr.Geometry(type=ogr.wkbLineString)
    bound_geom.AssignSpatialReference(src_srs)
    bound_geom.AddPoint_2D(envelope.left, envelope.top)
    bound_geom.AddPoint_2D(envelope.right, envelope.top)
    bound_geom.AddPoint_2D(envelope.right, envelope.bottom)
    bound_geom.AddPoint_2D(envelope.left, envelope.bottom)
    bound_geom.CloseRings()
    if segment_length is not None:
        bound_geom.Segmentize(segment_length)
    err = bound_geom.TransformTo(dst_srs)
    if err != 0:
        raise ProjectionError('Error projecting boundary: %s' % (err,))

    return Envelope(*bound_geom.GetEnvelope())
