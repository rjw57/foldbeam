import tango
import boundsutils
import cairoutils
import goocanvas
import gobject
import simple
import math
import gtk.gdk as gdk

class PadGadget(goocanvas.Rect, simple.SimpleItem, goocanvas.Item):
    __gproperties__ = {
        'orientation': ( int, None, None, 0, 3, tango.RIGHT, 
            gobject.PARAM_READWRITE ) ,
        'color-scheme': ( str, None, None, 'Plum', gobject.PARAM_READWRITE ) ,
        'pad-size': (float, None, None, 0.0, gobject.G_MAXFLOAT, 15.0,
            gobject.PARAM_READWRITE ) ,
    }

    def __init__(self, *args, **kwargs):
        self._bounds = goocanvas.Bounds()
        self._highlight_flag = False
        self._pad_data = {
            'orientation': tango.RIGHT,
            'color-scheme': 'Plum',
            'pad-size': 15.0,
        }
        self._model = None
        goocanvas.Rect.__init__(self, *args, **kwargs)
    
    def _get_internal_bounds(self):
        internal_bounds = boundsutils.align_to_integer_boundary( \
            goocanvas.Bounds(
                self.get_property('x'),
                self.get_property('y'),
                self.get_property('x') + self.get_property('width'),
                self.get_property('y') + self.get_property('height')))
        return internal_bounds
    
    def get_pad_size(self):
        return self.get_property('pad-size')
    
    def set_pad_size(self, value):
        self.set_property('pad-size', value)
    
    def get_color_scheme(self):
        return self.get_property('color-scheme')
    
    def set_color_scheme(self, color_scheme):
        self.set_property('color-scheme', color_scheme)
    
    def get_orientation(self):
        return self.get_property('orientation')
    
    def set_orientation(self, orientation):
        self.set_property('orientation', orientation)
    
    ## gobject methods
    def do_get_property(self, pspec):
        names = self._pad_data.keys()
        if(pspec.name in names):
            return self._pad_data[pspec.name]
        else:
            return goocanvas.Rect.do_get_property(self, pspec)
    
    def do_set_property(self, pspec, value):
        names = self._pad_data.keys()
        if(pspec.name in names):
            self._pad_data[pspec.name] = value
            self.changed(True)
            self.notify(pspec.name)
        else:
            goocanvas.Rect.do_set_property(self, pspec, value)

    ## we don't use the canvas concept of a model here because
    ## a pad model does not affect its positioning on the canvas.
    def set_pad_model(self, model):
        self._model = model

    def get_pad_model(self):
        return self._model
    
    ## simple item methods
    
    def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
        return simple.SimpleItem.do_simple_is_item_at(
            self, x, y, cr, is_pointer_event)

    def do_simple_create_path(self, cr):
        (x, y) = self.get_pad_location()
        tango.pad_boundary_curve(cr, x, y, self.get_orientation(),
            self.get_pad_size())
    
    def do_simple_paint(self, cr, bounds):
        my_bounds = self.get_bounds()
        if(not boundsutils.do_intersect(my_bounds, bounds)):
            return

        (x, y) = self.get_pad_location()

        well_color = None
        model = self.get_pad_model()
        if hasattr(model, 'well_color'):
            well_color = model.well_color

        tango.paint_pad(cr, self.get_color_scheme(), x, y,
            self.get_orientation(), self.get_pad_size(),
            highlight=self._highlight_flag, well_color=well_color)

        #cairoutils.rounded_rect(cr, self._get_internal_bounds(), 0, 0)
        #cr.set_source_rgb(1,0,0)
        #cr.fill()

    def get_pad_anchor(self):
        location = self.get_pad_location()
        return tango.pad_get_centre(location[0], location[1],
            self.get_orientation(), self.get_pad_size())
    
    def get_pad_location(self):
        int_bounds = self._get_internal_bounds()
        
        ## default x and y is to be in centre
        x = math.floor(0.5 * (int_bounds.x2 + int_bounds.x1)) + 0.5
        y = math.floor(0.5 * (int_bounds.y2 + int_bounds.y1)) + 0.5

        orientation = self.get_orientation()
        if(orientation == tango.RIGHT):
            x = int_bounds.x2
        elif(orientation == tango.LEFT):
            x = int_bounds.x1
        elif(orientation == tango.TOP):
            y = int_bounds.y1
        elif(orientation == tango.BOTTOM):
            y = int_bounds.y2

        return (x,y)
    
    ## event handlers
    def do_enter_notify_event(self, target, event):
        self._highlight_flag = True
        self.changed(False)
    
    def do_leave_notify_event(self, target, event):
        self._highlight_flag = False
        self.changed(False)

gobject.type_register(PadGadget)

## A pad is either an input or an output pad
INPUT, OUTPUT = range(2)

class PadModel(gobject.GObject):
    __gproperties__ = {
        'label': (str, 'Human readable pad name', None, 'Untitled',
            gobject.PARAM_READWRITE),
        'name': (str, 'Unique identifier for pad', None, 'untitled',
            gobject.PARAM_READWRITE),
        'type': (int, 'PAd type (input/output)', None, 0, 1, INPUT,
            gobject.PARAM_READWRITE),
        'parent': (gobject.TYPE_OBJECT, 'Pad\'s NodeModel parent', None,
            gobject.PARAM_READWRITE),
    }

    __gsignals__ = {
        'anchor-moved': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
    }

    def __init__(self, node_parent, *args, **kwargs):
        self._pad_data = {
            'label': 'Untitled',
            'name': 'untitled',
            'type': INPUT,
            'parent': node_parent,
            'graph': None,
        }
        self._anchor_location = (0, 0)
        self._model = None
        
        self._connected_edge_list = [ ]
        self._connected_edge_changed_handlers = { }

        self._graph_model = None

        gobject.GObject.__init__(self, *args, **kwargs)
    
    def get_n_connected_edges(self):
        return len(self._connected_edge_list)
    
    def get_connected_edges(self):
        return self._connected_edge_list
    
    def connected_to_edge(self, edge_model):
        graph_model = edge_model.get_graph_model()
        if(self._graph_model == None):
            self._graph_model = graph_model
            graph_model.connect('edge-removed', self._on_edge_removed)
        elif(self._graph_model != graph_model):
            raise ValueError('Attempt to connect pad to edge of different model.')
        elif(graph_model == None):
            raise ValueError('Edge has null graph model.')

        self._connected_edge_list.append(edge_model)
        handler_id = edge_model.connect('changed', self._on_edge_changed)
        self._connected_edge_changed_handlers[edge_model] = handler_id
    
    def disconnected_from_edge(self, edge_model):
        if(not edge_model in self._connected_edge_list):
            return
        self._connected_edge_list.remove(edge_model)
        edge_model.disconnect( \
            self._connected_edge_changed_handlers.pop(edge_model))
    
    def _on_edge_removed(self, graph, edge):
        self.disconnected_from_edge(edge)

    def _on_edge_changed(self, edge_model, recalculate_bounds):
        pads = (
            edge_model.get_property('start-pad'), 
            edge_model.get_property('end-pad') )
        if(not self in pads):
            self.disconnected_from_edge(edge_model)
    
    ## gobject methods
    def do_get_property(self, pspec):
        propnames = self._pad_data.keys()
        if(pspec.name in propnames):
            return self._pad_data[pspec.name]
        else:
            raise AttributeError('No such property: %s' % pspec.name)

    def do_set_property(self, pspec, value):
        propnames = self._pad_data.keys()
        if(pspec.name in propnames):
            self._pad_data[pspec.name] = value
            self.emit('changed')
            self.notify(pspec.name)
        else:
            raise AttributeError('No such property: %s' % pspec.name)

gobject.type_register(PadModel)


# vim:sw=4:ts=4:autoindent
