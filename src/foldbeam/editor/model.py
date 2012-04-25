import colorsys

import pygtk
import gobject
import gtk
import goocanvas
from foldbeam import graph, vector, tilestache
from foldbeam.graph import InputPad, OutputPad, can_connect, ConstantNode

from . import graphcanvas 
from ._sobol_seq import i4_sobol_generate

_type_colors = {}
def type_color(t):
    global _type_colors
    if t in _type_colors:
        return _type_colors[t]

    h = i4_sobol_generate(1, 1, len(_type_colors)+1)
    s = 0.8
    l = 0.3

    new_color = colorsys.hls_to_rgb(h,l,s)
    _type_colors[t] = new_color
    return new_color

class PadModel(graphcanvas.PadModel):
    __gsignals__ = {
        'value-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
    }

    def __init__(self, node_parent, pad, *args, **kwargs):
        graphcanvas.PadModel.__init__(self, node_parent, *args, **kwargs)
        self._pad = pad

    @property
    def well_color(self):
        return type_color(self._pad.type)

    def can_connect(self, other_pad):
        if isinstance(self._pad, InputPad) and isinstance(other_pad._pad, InputPad):
            return False
        if isinstance(self._pad, OutputPad) and isinstance(other_pad._pad, OutputPad):
            return False

        if isinstance(self._pad, InputPad):
            input_pad = self._pad
            output_pad = other_pad._pad
        else:
            input_pad = other_pad._pad
            output_pad = self._pad

        return can_connect(output_pad, input_pad)

    def connect_to(self, other_pad):
        if other_pad is None:
            self._pad.connect(None)
        else:
            self._pad.connect(other_pad._pad)

gobject.type_register(PadModel)

class FoldbeamNodeModel(graphcanvas.NodeModel):
    def __init__(self, node=None, *args, **kwargs):
        graphcanvas.NodeModel.__init__(self, *args, **kwargs)
        self.node = node
        self.set_property('node-title', node.__class__.__name__)

        self.is_removable = True
        self._output_pads = [ PadModel(self, v, type=graphcanvas.OUTPUT, label=k) for k,v in self.node.outputs.iteritems() ]
        self._input_pads = [ PadModel(self, v, type=graphcanvas.INPUT, label=k) for k,v in self.node.inputs.iteritems() ]

        self.node.input_pad_added.connect(self._input_pad_added)
        self.node.output_pad_added.connect(self._output_pad_added)

    def _input_pad_added(self, pad):
        self._input_pads.append(PadModel(self, pad, type=graphcanvas.INPUT, label=pad.name))
        self.pads_changed()

    def _output_pad_added(self, pad):
        self._output_pads.append(PadModel(self, pad, type=graphcanvas.OUTPUT, label=pad.name))
        self.pads_changed()

    ## pad query methods
    def get_n_output_pads(self):
        return len(self._output_pads)
    
    def get_output_pad(self, idx):
        return self._output_pads[idx]

    def get_n_input_pads(self):
        return len(self._input_pads)
    
    def get_input_pad(self, idx):
        return self._input_pads[idx]

gobject.type_register(FoldbeamNodeModel)

class ConstantNodeModel(FoldbeamNodeModel):
    def __init__(self, type_=str, type_cb=str, title=None, *args, **kwargs):
        super(ConstantNodeModel, self).__init__(node=ConstantNode(type_, ''), *args, **kwargs)
        self._entry = None
        self._type_cb = type_cb
        if title is not None:
            self.set_property('node-title', title)

    def create_widget(self):
        self._entry = gtk.Entry()
        self._entry.set_property('text', '')
        self._entry.connect('changed', self._on_changed)
        return self._entry

    def _on_changed(self, editable):
        self.node.value = self._type_cb(editable.get_property('text'))
        return True

gobject.type_register(ConstantNodeModel)
