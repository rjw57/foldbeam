import shapely.wkb

class IterableGeometry(object):
    """An object suitable for rendering with GeometryRenderer which simply stores an iterable of shapely geometry
    objects.

    .. py:attribute:: geom

        The iterable of shapely geometry objects.
    """
    def __init__(self, geom=None):
        self.geom = geom

    def within(self, boundary):
        """Returns *all* of :py:obj:`self.geom` or an empty list if it is `None`."""
        return self.geom or []

class GeoAlchemyGeometry(object):
    def __init__(self, query=None, geom_cls=None, geom_attr=None):
        self.query = query
        self.geom_cls = geom_cls
        self.geom_attr = geom_attr or 'geom'

    def within(self, boundary):
        if self.query is None:
            return []

        if self.geom_attr is None:
            return []

        q = self.query
        if self.geom_cls is not None:
            q = q.filter(getattr(self.geom_cls, self.geom_attr).intersects(boundary.wkt))

        return (shapely.wkb.loads(bytes(getattr(x, self.geom_attr).geom_wkb)) for x in q)
