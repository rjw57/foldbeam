from TileStache.Geography import Point

class Envelope(object):
    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    def top_left(self):
        return Point(self.left, self.top)

    def bottom_right(self):
        return Point(self.right, self.botom)

    def offset(self):
        """Return a tulple giving the offset from the top-left corner to the bottom right."""
        return (self.right - self.left, self.bottom - self.top)

    def __repr__(self):
        return 'Envelope(%f,%f,%f,%f)' % (self.left, self.right, self.top, self.bottom)

    def __str__(self):
        return '(%f => %f, %f => %f)' % (self.left, self.right, self.top, self.bottom)

