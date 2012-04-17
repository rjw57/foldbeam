from core import Boundary
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

def create_render_dataset(envelope, size=None, band_count=3, data_type=gdal.GDT_Byte):
    global _counter, _driver

    if size is None:
        size = envelope.size()

    _counter += 1
    name = '/vsimem/tmp/raster_%07d.tiff' % _counter
    raster = _driver.Create(name, size[0], size[1], band_count, data_type)

    # Set the dataset projection and geo transform
    raster.SetProjection(envelope.spatial_reference.ExportToWkt())
    xscale, yscale = [float(x[0])/float(x[1]) for x in zip(envelope.offset(), size)]
    raster.SetGeoTransform((envelope.left, xscale, 0, envelope.top, 0, yscale))

    return _DatasetWrapper(raster, name)
