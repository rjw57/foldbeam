"""Mechanisms for converting axis-aligned bounding boxes (:py:class:`Envelope`) and polygonal boundaries
(:py:class:`Boundary`) from one spatial reference system to another. It is used internally to convert the regions
represented by tiles between spatial references.
"""

from osgeo import ogr, gdal

def boundary_from_envelope(envelope):
    """Construct a :py:class:`Boundary` from an :py:class:`Envelope`. The boundary is the bounding box which encloses
    the envelope.

    :param envelope: the envelope to convert into a boundary
    :type envelope: :py:class:`Envelope`

    """

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
    """Error raised when projection from one spatial reference to another has failed.

    :param message: a description of the error
    :type message: str
    
    """

    def __init__(self, message):
        super(ProjectionError, self).__init__(message)

class Boundary(object):
    """A polygon defining an enclosing boundary for a region. A boundary *always* has an associated spatial reference.

    Generally you'll want to use the :py:func:`boundary_from_envelope` function to construct a boundary unless you have
    specific needs.

    :param geometry: boundary geometry
    :type geometry: :py:class:`ogr.Geometry` with polygon type

    .. py:data:: geometry

        An underlying instance of ogr.Geometry which specifies the boundary polygon.

    """

    def __init__(self, geometry):
        if geometry is None:
            raise ValueError('geometry cannot be None')
        if geometry.GetSpatialReference() is None:
            raise ValueError('geometry must have an associated spatial reference')

        self.geometry = geometry

    @property
    def wkt(self):
        return self.geometry.ExportToWkt()

    @property
    def envelope(self):
        """Calculate the bounding axis-aligned envelope which entirely contains this boundary.
        
        Since a boundary is an arbitrary polygon and an envelope is only an axis-aligned bounding box, the returned
        envelope will also contain point not within this boundary.

        :rtype: :py:class:`Envelope`

        """

        left, right, bottom, top = self.geometry.GetEnvelope()
        return Envelope(left, right, top, bottom, self.geometry.GetSpatialReference())

    def contains_point(self, x, y):
        """Convenience function to test if a point is contained within this boundary.

        :param x: the point's x-co-ordinate
        :type x: float
        :param y: the point's y-co-ordinate
        :type y: float
        :rtype: bool

        """

        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(x, y)
        return self.geometry.Contains(point)

    def transform_to(self, other_spatial_reference, src_seg_len=None, dst_seg_len=None):
        """Transform this boundary into another spatial reference.

        :param other_spatial_reference: the destination spatial reference
        :type other_spatial_reference: :py:class:`osr.SpatialReference`
        :param src_seg_len: the maximum length of a boundary segment in the source spatial reference
        :type src_seg_len: float or None
        :param dst_seg_len: the maximum length of a boundary segment in the detination spatial reference
        :type dst_seg_len: float or None
        :rtype: :py:class:`Boundary`

        This is a subtle function. The boundary is defined as a polygon of linear segments but, of course, lines do not
        necessarily map to lines in a projection. This function may optionally segmentise the boundary before
        transforming and simplify it afterwards.

        If *src_seg_len* is not None, it specifies the maximum length in the source spatial reference for boundary
        segments. If known, set this to the approximate length of a pixel in the source spatial reference.

        If *dst_seg_len* is not None, it specifies the maximum length in the destination spatial reference used to
        simplify the transformed boundary. If known, set this to the approximate length of a pixel in the destination
        spatial reference.
        
        """

        geom = self.geometry.Clone()
        if src_seg_len is not None:
            geom.Segmentize(float(src_seg_len))

        old_opt = gdal.GetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION')
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', 'TRUE')
        err = geom.TransformTo(other_spatial_reference)
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', old_opt)
        if err != 0:
            raise ProjectionError('Unable to project boundary into target projection (%s).' % (err,))

        if dst_seg_len is not None and hasattr(geom, 'Simplify'):
            geom.Simplify(dst_seg_len)

        return Boundary(geom)

    def __str__(self):
        return 'Boundary(%s, %s)' % (self.geometry, self.geometry.GetSpatialReference().ExportToPrettyWkt())

    def __repr__(self):
        return 'Boundary(%s, %s)' % (self.geometry, self.geometry.GetSpatialReference().ExportToWkt())

class Envelope(object):
    """An axis-aligned bounding box in a particular spatial reference.

    :param left: the left-most x co-ordinate
    :param right: the right-most x co-ordinate
    :param top: the top-most y co-ordinate
    :param bottom: the bottom-most y co-ordinate

    """

    def __init__(self, left, right, top, bottom, spatial_reference):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.spatial_reference = spatial_reference

    def top_left(self):
        """Obtain the top-left point for this envelope.

        :rtype: :py:class:`TileStache.Geography.Point`

        """
        return Point(self.left, self.top)

    def bottom_right(self):
        """Obtain the bottom-right point for this envelope.

        :rtype: :py:class:`TileStache.Geography.Point`

        """
        return Point(self.right, self.bottom)

    def offset(self):
        """Return a tuple giving the offset from the top-left corner to the bottom right."""
        return (self.right - self.left, self.bottom - self.top)

    def size(self):
        """Return a tuple giving the *absolute* offset from the top-left corner to the bottom right."""
        return [abs(x) for x in self.offset()]

    def transform_to(self, other_spatial_reference, src_seg_len=None, dst_seg_len=None):
        """Return a envelope which contains this envelope in a target spatial reference.

        This is a convenience function which converts the envelope into a rectangular boundary, transforms it and
        returns the envelope of the resulting boundary.

        :param other_spatial_reference: the destination spatial reference
        :type other_spatial_reference: :py:class:`osr.SpatialReference`
        :param src_seg_len: the maximum length of a boundary segment in the source spatial reference
        :type src_seg_len: float or None
        :param dst_seg_len: the maximum length of a boundary segment in the detination spatial reference
        :type dst_seg_len: float or None
        :rtype: :py:class:`Envelope`

        """
        return boundary_from_envelope(self). \
            transform_to(other_spatial_reference, src_seg_len, dst_seg_len).envelope

    def __repr__(self):
        return 'Envelope(%f,%f,%f,%f)' % (self.left, self.right, self.top, self.bottom)

    def __str__(self):
        return '(%f => %f, %f => %f)' % (self.left, self.right, self.top, self.bottom)
