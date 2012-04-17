import json
from TileStache.Geography import Point
from osgeo import ogr

def boundary_from_envelope(envelope):
    wkt = 'POLYGON ((%s))' % (
            ','.join(['%f %f' % x for x in [
                (envelope.left,envelope.top),
                (envelope.right,envelope.top),
                (envelope.right,envelope.bottom),
                (envelope.left,envelope.bottom),
                (envelope.left,envelope.top)
            ]]),
    )
    geom = ogr.CreateGeometryFromWkt(wkt)
    geom.AssignSpatialReference(envelope.spatial_reference)
    return Boundary(geom)

class ProjectionError(RuntimeError):
    def __init__(self, message):
        super(ProjectionError, self).__init__(message)

class Boundary(object):
    def __init__(self, geometry):
        """A single polygon defining an enclosing boundary for a region.

        :param geometry: boundary geometry
        :type geometry: obr.Geometry with polygon type

        .. py:data:: geometry
            An underlying instance of ogr.Geometry which specifies the boundary polygon.

        """

        if geometry is None:
            raise ValueError('geometry cannot be None')
        if geometry.GetSpatialReference() is None:
            raise ValueError('geometry must have an associated spatial reference')

        self.geometry = geometry

    def envelope(self):
        l,r,b,t = self.geometry.GetEnvelope()
        return Envelope(l,r,t,b,self.geometry.GetSpatialReference())

    def contains_point(self, x, y):
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint_2D(x,y)
        return self.geometry.Contains(pt)

    def transform_to(self, other_spatial_reference, src_seg_len=None, dst_seg_len=None):
        geom = self.geometry.Clone()
        if src_seg_len is not None:
            geom.Segmentize(float(src_seg_len))

        err = geom.TransformTo(other_spatial_reference)
        if err != 0:
            raise ProjectionError('Unable to project boundary into target projection (%s).' % (err,))

        if dst_seg_len is not None:
            geom.Simplify(dst_seg_len)

        return Boundary(geom)

    def __str__(self):
        return 'Boundary(%s, %s)' % (self.geometry, self.geometry.GetSpatialReference().ExportToPrettyWkt())

    def __repr__(self):
        return 'Boundary(%s, %s)' % (self.geometry, self.geometry.GetSpatialReference().ExportToWkt())

class Envelope(object):
    def __init__(self, left, right, top, bottom, spatial_reference):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.spatial_reference = spatial_reference

    def top_left(self):
        return Point(self.left, self.top)

    def bottom_right(self):
        return Point(self.right, self.botom)

    def offset(self):
        """Return a tulple giving the offset from the top-left corner to the bottom right."""
        return (self.right - self.left, self.bottom - self.top)

    def size(self):
        return map(abs, self.offset())

    def transform_to(self, other_spatial_reference, src_seg_len=None, dst_seg_len=None):
        return boundary_from_envelope(self). \
            transform_to(other_spatial_reference, src_seg_len, dst_seg_len).envelope()

    def __repr__(self):
        return 'Envelope(%f,%f,%f,%f)' % (self.left, self.right, self.top, self.bottom)

    def __str__(self):
        return '(%f => %f, %f => %f)' % (self.left, self.right, self.top, self.bottom)

