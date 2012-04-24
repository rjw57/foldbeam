"""
The nodal compositing model
===========================

Foldbeam makes use of a nodal computation model where data flow from source nodes to sink nodes through directed edges.
Each node may have multiple input or output 'pads' which edges can be connected to. When a particular node is asked for
the value of one of it's output pads, the node may pull data along from an input node along an input edge.

"""

import collections
from notify.all import Signal
import weakref

node_classes = []
def node(cls):
    global node_classes
    node_classes.append(cls)
    return cls

class Pad(object):
    def __init__(self, type_, container, name):
        super(Pad, self).__init__()
        self.type = type_
        self.name = name
        self._container = weakref.ref(container)

    @property
    def container(self):
        return self._container()

class InputPad(Pad):
    """A pad which can act as an input to a node. An :py:class:`InputPad` can be connected to an :py:class:`OutputPad`
    to implicitly form an edge along which data can flow. Multiple :py:class:`InputPad` instances can be connected to
    the same :py:class:`OutputPad`.

    The pad's source pad is kept as a weak reference meaning that the implicit edge will go away if the source pad is
    garbage collected. The pad's container is also kept as a weak reference in order to break reference cycles.

    :param type_: the 'type' of this pad (see :py:func:`can_connect`).
    :param container: the container object of this pad
    :type container: usually a :py:class:`Node`-derived class
    :param name: a human-readble name for this pad
    :type name: :py:class:`str`

    .. py:data:: container

        A strong reference to this pad's container or :py:const:`None` if the container was not set or has been garbage
        collected.

    .. py:data:: source

        A strong reference to the pad this pad is connected to or :py:const:`None` if this pad is connected to no other pad.

    """

    def __init__(self, type_, container, name):
        super(InputPad, self).__init__(type_, container, name)
        self._source = None

    @property
    def source(self):
        return self._source()

    def __call__(self, **kwargs):
        if self._source is None:
            return None

        src_pad = self._source()
        if src_pad is None:
            self._source = None
            return None

        return src_pad(**kwargs)

    def pull(self, **kwargs):
        return self(**kwargs)

    def connect(self, pad=None):
        self._source = weakref.ref(pad) if pad is not None else None

class OutputPad(Pad):
    """A pad which can act as an output to a node. An :py:class:`InputPad` can be connected to an :py:class:`OutputPad`
    to implicitly form an edge along which data can flow. Multiple :py:class:`InputPad` instances can be connected to
    the same :py:class:`OutputPad`.

    An :py:class:`OutputPad` can be called to pull data out of the pad.

    :param type_: the 'type' of this pad (see :py:func:`can_connect`).
    :param container: the container object of this pad
    :type container: usually a :py:class:`Node`-derived class
    :param name: a human-readble name for this pad
    :type name: :py:class:`str`
    :param pull: a function which is to be called to pull data from this pad
    :type pull: callable

    .. py:data:: container

        A strong reference to this pad's container or :py:const:`None` if the container was not set or has been garbage
        collected.

    .. py:data:: damaged

        A signal which can be connected to to be notified when the contents which can be pulled from this pad have
        changed. Connect to it by passing a callable to the :py:meth:`damaged.connect` method::

            def damage_cb(boundary):
                recalculate_envelope(boundary.envelope)

            # ... pad is the OutputPad of interest
            pad.damaged.connect(damage_cb)

        The callable should accept a single parameter which is a :py:class:`Boundary` specifying the geographic area in
        which the output has changed. This can be :py:const:`None` in which case it is assumed that the output should
        always be pulled from.

        To notify listeners that an :py:class:`OutputPad` had new data, call the :py:attr:`damaged` signal directly::
        
            # ... pad is the OutputPad of interest

            # Notify any listeners that a specific region of the pad has changed:
            boundary = Boundary(
                # ...
            )
            pad.damaged(boundary)

            # Notify any listeners that all regions of the pad have changed:
            pad.damaged(None)
    """
    def __init__(self, type_, container, name, pull):
        super(OutputPad, self).__init__(type_, container, name)
        self.damaged = Signal()
        self._pull = pull

    def __call__(self, **kwargs):
        return self._pull(**kwargs)

class PadCollection(collections.OrderedDict):
    """A collection of pads which can be iterated over and indexed like a dictionary with the wrinkle that pads are
    returned in the order they are added.

    .. py:data:: pad_name

        If compatible with Python's naming convention, each pad is accessible as an attribute of the collection as well
        as indexing explicitly by name via the [] operator.

    """

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
    """A single node in the data flow graph which has inputs and outputs. A node may contain 'sub-nodes' within it.

    Usually you wont create instances of this class directly. Instead you will create one of its derived classes. This
    class contains functionality common to all nodes.

    .. py:data:: inputs

        A :py:class:`PadCollection` instance of input pads.

    .. py:data:: outputs

        A :py:class:`PadCollection` instance of output pads.

    .. py:data:: subnodes

        A sequence of sub-nodes which exist within this node and are used to generate its output.

    """

    def __init__(self):
        self.inputs = PadCollection()
        self.outputs = PadCollection()
        self.subnodes = []

    def add_subnode(self, node):
        """
        Add a node to the list of sub-nodes for this node. If you create any nodes implicitly within a derived node's
        constructor they should be added here. This function returns *node* meaning it can be used like this::
        
            class MyNode(Node):
                def __init__(self, default=None):
                    # create inputs...

                    if default is not None:
                        default_node = self.add_node(ConstantNode(str, default))
                        # connect default node to input pad
        """

        self.subnodes.append(node)
        return node

    def add_input(self, name, type_, default=None):
        """
        Add an input pad to this node. If *default* is not :py:const:`None` then a :py:class:`ConstantNode` is
        implicitly created and connected to the input.

        """
        assert name not in self.inputs
        self.inputs[name] = InputPad(type_, self, name)
        if default is not None:
            const_node = self.add_subnode(ConstantNode(type_, default))
            connect(const_node.outputs['value'], self.inputs[name])

    def add_output(self, name, type_, pad_cb):
        """
        Add an output pad to this node.

        :param pad_cb: called when the output pad is pulled from
        :type pad_cb: callable

        """
        assert name not in self.outputs
        self.outputs[name] = OutputPad(type_, self, name, pad_cb)

def can_connect(src_pad, dst_pad):
    """
    Checks if the types of two pads are compatible for connection. Currently this simply checks that
    :py:attr:`src_pad.type` is the same object as :py:attr:`dst_pad.type`. Should a more sophisticated type-munging
    scheme be added, this function will be updated and so this function should be used in preference to checking the
    types directly.
    
    """
    if src_pad is None or dst_pad is None:
        return False

    if src_pad.type is dst_pad.type:
        return True

    return False

def connect(src_pad, dst_pad):
    """
    Connect a source pad to a destination pad so that data may flow along an edge. A single source pad may be connected
    to multiple destination pads. If the source or destination is garbage collected, the edge is implicitly removed.

    :param src_pad: the pad to draw data from
    :type src_pad: :py:class:`OutputPad`
    :param dst_pad: the pad to push data to
    :type dst_pad: :py:class:`InputPad`

    :raise ValueError: if any of the source or destination containers are :py:const:`None`.
    :raise ValueError: if the source and destination pad types are incompatible (see :py:func:`can_connect`).

    """
    dst_node = dst_pad.container
    src_node = src_pad.container

    if src_node is None:
        raise ValueError('Source pad has no container')

    if dst_node is None:
        raise ValueError('Destination pad has no container')

    if not can_connect(src_pad, dst_pad):
        raise ValueError(
                'Source and destination pads have incompatible types: %s and %s' % (src_pad.type, dst_pad.type))

    dst_pad.connect(src_pad)

class ConstantNode(Node):
    def __init__(self, type_, value):
        super(ConstantNode, self).__init__()
        self.add_output('value', type_, lambda: value)

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
