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
