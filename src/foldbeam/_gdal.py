import core
from osgeo import gdal, ogr
import numpy as np

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
        spatial_reference)

class _DatasetWrapper(object):
    def __init__(self, dataset, filename):
        self.dataset = dataset
        self.filename = filename

    def write_tiff(self, filename):
        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy(filename, self.dataset)

    def __del__(self):
        if self.filename is not None:
            gdal.Unlink(self.filename)

_counter = 0
def create_render_dataset(envelope, size=None, band_count=3, data_type=gdal.GDT_Byte, prototype_ds=None):
    global _counter
    driver = gdal.GetDriverByName('MEM')
    assert driver is not None

    if size is None:
        size = map(int, envelope.size())

    if prototype_ds is not None:
        band_count = prototype_ds.RasterCount
        data_type = prototype_ds.GetRasterBand(1).DataType

    _counter += 1
    raster = driver.Create('', size[0], size[1], band_count, data_type)
    assert raster is not None

    # Set the dataset projection and geo transform
    raster.SetProjection(envelope.spatial_reference.ExportToWkt())
    xscale, yscale = [float(x[0])/float(x[1]) for x in zip(envelope.offset(), size)]
    raster.SetGeoTransform((envelope.left, xscale, 0, envelope.top, 0, yscale))

    if prototype_ds is not None:
        for idx in xrange(1, band_count+1):
            dst_band = raster.GetRasterBand(idx)
            src_band = prototype_ds.GetRasterBand(idx)
            dst_band.SetColorTable(src_band.GetColorTable())
            dst_band.SetColorInterpretation(src_band.GetColorInterpretation())
    elif band_count == 4:
        raster.GetRasterBand(1).SetColorInterpretation(gdal.GCI_RedBand)
        raster.GetRasterBand(2).SetColorInterpretation(gdal.GCI_GreenBand)
        raster.GetRasterBand(3).SetColorInterpretation(gdal.GCI_BlueBand)
        raster.GetRasterBand(3).SetColorInterpretation(gdal.GCI_AlphaBand)
    elif band_count == 3:
        raster.GetRasterBand(1).SetColorInterpretation(gdal.GCI_RedBand)
        raster.GetRasterBand(2).SetColorInterpretation(gdal.GCI_GreenBand)
        raster.GetRasterBand(3).SetColorInterpretation(gdal.GCI_BlueBand)
    elif band_count == 1:
        raster.GetRasterBand(1).SetColorInterpretation(gdal.GCI_GrayIndex)

    return _DatasetWrapper(raster, None)
