from functools import wraps

from osgeo import ogr

import shapely.wkb

def reproject_from_native_spatial_reference(f):

    @wraps(f)
    def within(self, boundary, spatial_reference=None, **kwargs):
        # Find the native spatial reference
        native_spatial_reference = self.native_spatial_reference

        # If no spatial reference was specified, or if it matches the native one, just render directly
        if native_spatial_reference is None or spatial_reference is None or spatial_reference.IsSame(native_spatial_reference):
            return f(self, boundary, spatial_reference=native_spatial_reference, **kwargs)

        def reproj(g):
            geom = ogr.CreateGeometryFromWkb(g.wkb)
            geom.AssignSpatialReference(native_spatial_reference)
            geom.TransformTo(spatial_reference)
            return shapely.wkb.loads(geom.ExportToWkb())

        geoms = f(self,
                boundary.transform_to(native_spatial_reference),
                spatial_reference=native_spatial_reference,
                **kwargs)

        return (reproj(x) for x in geoms)

    return within

class IterableGeometry(object):
    """An object suitable for rendering with GeometryRenderer which simply stores an iterable of shapely geometry
    objects.

    .. py:attribute:: geom

        The iterable of shapely geometry objects.
    """
    def __init__(self, geom=None):
        self.geom = geom
        self.native_spatial_reference = None

    @reproject_from_native_spatial_reference
    def within(self, boundary, spatial_reference=None):
        """Returns *all* of :py:obj:`self.geom` or an empty list if it is `None`."""
        return self.geom or []

class GeoAlchemyGeometry(object):
    def __init__(self, query=None, geom_cls=None, geom_attr=None, spatial_reference=None):
        self.query = query
        self.geom_cls = geom_cls
        self.geom_attr = geom_attr or 'geom'
        self.native_spatial_reference = spatial_reference

    @reproject_from_native_spatial_reference
    def within(self, boundary, spatial_reference=None):
        if self.query is None:
            return []

        if self.geom_attr is None:
            return []

        q = self.query
        if self.geom_cls is not None:
            q = q.filter(getattr(self.geom_cls, self.geom_attr).intersects(boundary.wkt))

        return (shapely.wkb.loads(bytes(getattr(x, self.geom_attr).geom_wkb)) for x in q)
