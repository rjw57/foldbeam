from notify.all import Signal

class ContentType(object):
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
