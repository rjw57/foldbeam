from . import graphcanvas 
from foldbeam.graph import InputPad, OutputPad, can_connect
import pygtk
import gobject
import gtk
import goocanvas

class PadModel(graphcanvas.PadModel):
    __gsignals__ = {
        'value-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
    }

    def __init__(self, node_parent, pad, *args, **kwargs):
        graphcanvas.PadModel.__init__(self, node_parent, *args, **kwargs)
        self._pad = pad

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

    def get_value(self):
        return self._pad

    def set_value(self, value):
        self._pad.connect(value)

gobject.type_register(PadModel)

class FoldbeamNodeModel(graphcanvas.NodeModel):
    __gsignals__ = {
        'contents-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
    }

    def __init__(self, node=None, *args, **kwargs):
        graphcanvas.NodeModel.__init__(self, *args, **kwargs)
        self.node = node
        self.set_property('node-title', node.__class__.__name__)

        self._output_pads = [ PadModel(self, v, type=graphcanvas.OUTPUT, label=k) for k,v in self.node.outputs.iteritems() ]
        self._input_pads = [ PadModel(self, v, type=graphcanvas.INPUT, label=k) for k,v in self.node.inputs.iteritems() ]

    def contents_changed(self):
        self.emit('contents-changed')
    
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
