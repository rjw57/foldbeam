import collections

class EdgeType(object):
    def useable_as(self, other_type):
        return other_type is self

class NamedType(object):
    @classmethod
    def get_description(cls):
        return cls.__name__

class RasterType(NamedType):
    pass

class FloatType(NamedType):
    pass

class Pad(object):
    IN      = 'IN'
    OUT     = 'OUT'

    def __init__(self, direction, type):
        self.direction = direction
        self.type = type

class PadCollection(collections.OrderedDict):
    def __init__(self, *args, **kwargs):
        super(PadCollection, self).__init__(*args, **kwargs)

    def __getattr__(self, name):
        try:
            return getattr(super(PadCollection, self), name)
        except AttributeError as e:
            if name in self:
                return self[name]
            raise e

class Node(object):
    def __init__(self):
        self.inputs = PadCollection()
        self.outputs = PadCollection()
        self.subnodes = []

    def add_subnode(self, node):
        self.subnodes.append(node)

    def add_input(self, name, pad):
        assert name not in self.inputs
        assert pad.direction is Pad.IN
        self.inputs[name] = pad

    def add_output(self, name, pad):
        assert name not in self.outputs
        assert pad.direction is Pad.OUT
        self.outputs[name] = pad
