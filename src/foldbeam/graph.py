import pads

class Node(object):
    def __init__(self):
        self.pads = { }

    def add_pad(self, name, pad):
        assert name not in self.pads
        self.pads[name] = pad
