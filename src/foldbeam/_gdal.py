from osgeo import gdal, ogr

_counter = 0
_driver = gdal.GetDriverByName('GTiff')

def create_render_dataset(envelope, envelope_srs, size=None, band_count=3, data_type=gdal.GDT_Byte):
    global _counter, _driver

    if size is None:
        size = [abs(x) for x in envelope[2:]]

    _counter += 1
    name = '/vsimem/tmp/raster_%07d.tiff' % _counter
    raster = _driver.Create(name, size[0], size[1], band_count, data_type)

    # Set the dataset projection and geo transform
    raster.SetProjection(envelope_srs.ExportToWkt())
    xscale = float(envelope[2]) / float(size[0])
    yscale = float(envelope[3]) / float(size[1])
    raster.SetGeoTransform((envelope[0], xscale, 0, envelope[1], 0, yscale))

    return raster

def transform_envelope(envelope, src_srs, dst_srs, segment_length=None):
    """envelope is a tuple giving the (left, top, width, height) of an envelope in the src_srs ogr.SpatialReference.
    Return the corresponding envelope in the dts_srs ogr.SpatialReference.

    If segment_length is not None it is the maximum length *in the source SRS* to segment the boundary by.

    """

    # Test for identity transform
    if src_srs.IsSame(dst_srs):
        return envelope

    # Create polygon representing envelope
    bound_geom = ogr.Geometry(type=ogr.wkbLineString)
    bound_geom.AssignSpatialReference(src_srs)
    bound_geom.AddPoint_2D(envelope[0],                   envelope[1])
    bound_geom.AddPoint_2D(envelope[0],                   envelope[1] + envelope[3])
    bound_geom.AddPoint_2D(envelope[0] + envelope[2],   envelope[1] + envelope[3])
    bound_geom.AddPoint_2D(envelope[0] + envelope[2],   envelope[1])
    bound_geom.CloseRings()
    if segment_length is not None:
        bound_geom.Segmentize(segment_length)
    err = bound_geom.TransformTo(dst_srs)
    if err != 0:
        raise RuntimeError('Error projecting boundary: %s' % (err,))

    x1, x2, y1, y2 = bound_geom.GetEnvelope()
    return (x1, y1, x2-x1, y2-y1)
