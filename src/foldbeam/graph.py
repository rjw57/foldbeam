import collections

class Pad(object):
    IN      = 'IN'
    OUT     = 'OUT'

    def __init__(self, direction, type):
        self.direction = direction
        self.type = type

class InputPad(Pad):
    def __init__(self, type, default=None):
        super(InputPad, self).__init__(Pad.IN, type)
        self._default = ConstantOutputPad(type, default)
        self._source = None

    @property
    def source(self):
        return self._source if self._source is not None else self._default

    @source.setter
    def source(self, value):
        self._source = value

    def __call__(self, **kwargs):
        return self.pull(**kwargs)

    def connect(self, pad=None):
        self.source = pad

    def pull(self, **kwargs):
        return self.source(**kwargs)

class OutputPad(Pad):
    def __init__(self, type):
        super(OutputPad, self).__init__(Pad.OUT, type)

    def __call__(self, **kwargs):
        return self.pull(**kwargs)

    def pull(self, **kwargs):
        return None

class ConstantOutputPad(OutputPad):
    def __init__(self, type, value=None):
        super(ConstantOutputPad, self).__init__(type)
        self.value = value

    def __call__(self, **kwargs):
        return self.pull(**kwargs)

    def pull(self, **kwargs):
        return self.value

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

    def add_input(self, name, type_, default=None):
        assert name not in self.inputs
        self.inputs[name] = InputPad(type_)
        if default is not None:
            self.inputs[name].connect(ConstantOutputPad(type_, default))

    def add_output(self, name, pad):
        assert name not in self.outputs
        assert pad.direction is Pad.OUT
        self.outputs[name] = pad

class ConstantNode(Node):
    def __init__(self, type_, value):
        super(ConstantNode, self).__init__()
        self.add_output(ConstantOutputPad(type_, value))

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
