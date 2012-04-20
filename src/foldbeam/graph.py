import pads

class Node(object):
    def __init__(self):
        self.pads = { }
        self.pad_names = []
        self.subnodes = []

    def add_subnode(self, node):
        self.subnodes.append(node)

    def add_pad(self, name, pad):
        assert name not in self.pads
        self.pads[name] = pad
        self.pad_names.append(name)
