import core
from notify.all import Signal
import numpy as np

class ContentType(object):
    NONE = 'application/octet-stream; application=vnd.null'
    PNG = 'image/png'
    JPG = 'image/jpeg'
    GEOJSON = 'application/json; application=geojson'   # This is cooked up!
    RASTER = 'application/vnd.python.reference; application=datasetwrapper'

class Node(object):
    def __init__(self):
        self.outputs = { }

    def set_input(self, key, value):
        raise KeyError('no such input: ' + key)

    def __setitem__(self, key, value):
        self.set_input(key, value)

class OutputPad(object):
    def __init__(self):
        self.damaged = Signal()

    def __call__(self, envelope, size=None):
        return self.pull(envelope, size)

    def pull(self, envelope, size=None):
        return None

    def notify_damage(self, envelope):
        """Push a region which has been invalidated."""

        self.damaged(envelope)

class CallableOutputPad(OutputPad):
    def __init__(self, cb):
        super(CallableOutputPad, self).__init__()
        self._cb = cb

    def pull(self, envelope, size=None):
        return self._cb(envelope, size)

class RasterOutputPad(CallableOutputPad):
    def __init__(self, render_cb):
        super(RasterOutputPad, self).__init__(self._render_raster)
        self._render_cb = render_cb

    def _render_raster(self, envelope, size=None):
        if size is None:
            size = map(int, envelope.size())

        tile_size = 256
        tiles = []
        xscale, yscale = [x[0] / float(x[1]) for x in zip(envelope.offset(), size)]
        for x in xrange(0, size[0], tile_size):
            width = min(x + tile_size, size[0]) - x
            for y in xrange(0, size[1], tile_size):
                height = min(y + tile_size, size[1]) - y
                tile_envelope = core.Envelope(
                        envelope.left + xscale * x,
                        envelope.left + xscale * (x + width),
                        envelope.top + yscale * y,
                        envelope.top + yscale * (y + height),
                        envelope.spatial_reference,
                )
                tile_raster = self._render_cb(tile_envelope, (width, height))
                if tile_raster is not None:
                    tiles.append(((x,y), tile_raster))

        if len(tiles) == 0:
            return ContentType.NONE, None

        # FIXME: This assumes that to_rgba_cb is the same for each tile
        to_rgba = tiles[0][1].to_rgba_cb
        depth = tiles[0][1].array.shape[2]

        shape = (size[1], size[0])
        mask = np.ones(shape + (depth,), dtype=np.bool)
        data = np.zeros(shape + (depth,), dtype=np.float32)
        for pos, tile in tiles:
            x, y = pos
            h, w = tile.array.shape[:2]
            print(tile.array.shape)

            tile_mask = np.ma.getmask(tile.array)
            if tile_mask is np.ma.nomask:
                tile_mask = False

            mask[y:(y+h), x:(x+w), :] = tile_mask
            data[y:(y+h), x:(x+w), :] = tile.array

        if np.any(mask):
            data = np.ma.array(data, mask=mask)
        return ContentType.RASTER, core.Raster(data, envelope, to_rgba)

