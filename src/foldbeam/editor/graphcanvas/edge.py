import tango
import boundsutils
import cairoutils
import cairo
import goocanvas
import gobject
import simple
import math
import padgadget

class EdgeItem(goocanvas.ItemSimple, simple.SimpleItem, goocanvas.Item):
    ''' An edge item represents an edge in the graph. It joins a start
        anchor location to an end anchor location. If it has an associated
        GraphItem and EdgeModel, this will be used to automatically move the
        anchors to match the pads specified in the EdgeModel. '''

    __gproperties__ = {
        'start-anchor-x': ( float, None, None, 
            -gobject.G_MAXFLOAT, gobject.G_MAXFLOAT, 0.0,
            gobject.PARAM_READWRITE ) ,
        'start-anchor-y': ( float, None, None, 
            -gobject.G_MAXFLOAT, gobject.G_MAXFLOAT, 0.0,
            gobject.PARAM_READWRITE ) ,
        'end-anchor-x': ( float, None, None, 
            -gobject.G_MAXFLOAT, gobject.G_MAXFLOAT, 0.0,
            gobject.PARAM_READWRITE ) ,
        'end-anchor-y': ( float, None, None, 
            -gobject.G_MAXFLOAT, gobject.G_MAXFLOAT, 0.0,
            gobject.PARAM_READWRITE ) ,
        'edge-width': ( float, None, None, 
            0.0, gobject.G_MAXFLOAT, 9.0,
            gobject.PARAM_READWRITE ) ,
        'color-scheme': ( str, None, None, 'Butter', 
            gobject.PARAM_READWRITE ) ,
        'invalid-color-scheme': ( str, None, None, 'Scarlet Red', 
            gobject.PARAM_READWRITE ) ,
    }

    def __init__(self, *args, **kwargs):
        self._bounds = goocanvas.Bounds()

        ## EdgeItem only properties.
        self._edge_data = {
            'start-anchor-x': 0.0,
            'start-anchor-y': 0.0,
            'end-anchor-x': 0.0,
            'end-anchor-y': 0.0,
            'edge-width': 9.0,
        }

        ## Shared EdgeModel and EdgeItem properties.
        self._edge_model_data = {
            'color-scheme': 'Butter',
            'invalid-color-scheme': 'Scarlet Red',
            'graph-model': None,
            'start-pad': None,
            'end-pad': None,
        }

        ## the parent GraphItem
        self._graph_item = None

        goocanvas.ItemSimple.__init__(self, *args, **kwargs)

    def get_edge_width(self):
        return self.get_property('edge-width')
    
    def set_edge_width(self, edge_width):
        self.set_property('edge-width', edge_width)

    def get_color_scheme(self):
        return self.get_property('color-scheme')
    
    def set_color_scheme(self, color_scheme):
        self.set_property('color-scheme', color_scheme)

    def get_invalid_color_scheme(self):
        return self.get_property('invalid-color-scheme')
    
    def set_invalid_color_scheme(self, invalid_color_scheme):
        self.set_property('invalid-color-scheme', invalid_color_scheme)
    
    def get_start_anchor(self):
        return ( \
            self.get_property('start-anchor-x'),
            self.get_property('start-anchor-y') )
    
    def set_start_anchor(self, x, y):
        self.set_property('start-anchor-x', x)
        self.set_property('start-anchor-y', y)
    
    def get_end_anchor(self):
        return ( \
            self.get_property('end-anchor-x'),
            self.get_property('end-anchor-y') )
    
    def set_end_anchor(self, x, y):
        self.set_property('end-anchor-x', x)
        self.set_property('end-anchor-y', y)

    def is_valid(self):
        ''' Work out if this edge is valid based on whether
            there is a pad under the start and end anchor. '''

        ## if we have a model, ask it whether or not we're valid
        model = self.get_model()

        if(model != None):
            return model.is_valid()
        else:
            start = self.get_start_anchor()
            end = self.get_end_anchor()
            start_pad = self._get_pad_at(*start)
            end_pad = self._get_pad_at(*end)

            if(start_pad != None):
                start_pad_model = start_pad.get_pad_model()
            else:
                start_pad_model = None

            if(end_pad != None):
                end_pad_model = end_pad.get_pad_model()
            else:
                end_pad_model = None

        ## if there isn't a pad at both ends, edge is invalid
        if((end_pad_model == None) or (start_pad_model == None)):
            return False

        ## if either end is wrong type, pad is invalid
        if(start_pad_model.get_property('type') != padgadget.OUTPUT):
            return False
        if(end_pad_model.get_property('type') != padgadget.INPUT):
            return False

        ## if the end pad already has a connection, the edge is 
        ## invalid - i.e. inputs can only have one connection.
        if(end_pad_model.get_n_connected_edges() > 0):
            return False

        ## Test for connectivity as specified by the pad models themselves
        if hasattr(start_pad_model, 'can_connect') and not start_pad_model.can_connect(end_pad_model):
            return False
        if hasattr(end_pad_model, 'can_connect') and not end_pad_model.can_connect(start_pad_model):
            return False

        return True
    
    def get_graph_item(self):
        return self._graph_item
    
    def set_graph_item(self, graph):
        self._graph_item = graph
        graph.connect('pad-anchor-changed', self._on_pad_anchor_changed)
        self._update_anchor_locations()

    ## gobject methods
    def do_get_property(self, pspec):
        names = self._edge_data.keys()
        model_names = self._edge_model_data.keys()
        if(pspec.name in names):
            return self._edge_data[pspec.name]
        elif(pspec.name in model_names):
            return self._edge_model_data[pspec.name]
        else:
            return goocanvas.ItemSimple.do_get_property(pspec)
    
    def do_set_property(self, pspec, value):
        names = self._edge_data.keys()
        model_names = self._edge_model_data.keys()
        if(pspec.name in names):
            self._edge_data[pspec.name] = value
        elif(pspec.name in model_names):
            self._edge_model_data[pspec.name] = value
        else:
            goocanvas.ItemSimple.do_set_property(pspec, value)
            return
        self.changed(True)
        self.notify(pspec.name)
    
    ## simple item methods
    def set_model(self, model):
        goocanvas.ItemSimple.set_model(self, model)

        # so nasty
        self._edge_model_data = model._edge_data

        model.connect('changed', self._on_model_changed)
        self._on_model_changed(model, True)
    
    def _on_pad_anchor_changed(self, graph, pad_model, x, y):
        model = self.get_model()
        if(model == None):
            return
        start_pad_model = model.get_property('start-pad')
        end_pad_model = model.get_property('end-pad')
        if((pad_model != start_pad_model) and (pad_model != end_pad_model)):
            return
        self._update_anchor_locations()
    
    def _update_anchor_locations(self):
        graph_item = self.get_graph_item()
        model = self.get_model()
        if((model != None) and (graph_item != None)):
            start_pad_model = model.get_property('start-pad')
            end_pad_model = model.get_property('end-pad')
            if(end_pad_model != None):
                loc = graph_item.get_pad_anchor(end_pad_model)
                self.set_property('end-anchor-x', loc[0])
                self.set_property('end-anchor-y', loc[1])
            if(start_pad_model != None):
                loc = graph_item.get_pad_anchor(start_pad_model)
                self.set_property('start-anchor-x', loc[0])
                self.set_property('start-anchor-y', loc[1])
        self.changed(True)

    def _on_model_changed(self, model, recompute_bounds):
        if(model != None):
            start_pad = model.get_property('start-pad')
            end_pad = model.get_property('end-pad')
            self._update_anchor_locations()
        self.changed(True)
    
    def do_simple_update(self, cr):
        width = self.get_edge_width()
        bounds = boundsutils.inset(self._get_internal_bounds(),
            -0.5 * width, -0.5 * width)
        self.bounds_x1 = bounds.x1
        self.bounds_y1 = bounds.y1
        self.bounds_x2 = bounds.x2
        self.bounds_y2 = bounds.y2
    
    def _get_pad_at(self, x, y):
        items = self.get_canvas().get_items_at(x,y,False)
        pad_item = None
        if(items != None):
            for item in items:
                if(isinstance(item, padgadget.PadGadget)):
                    pad_item = item
        return pad_item

    def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
        return False
    
    def _get_internal_bounds(self):
        start = self.get_start_anchor()
        end = self.get_end_anchor()
        minx = min(start[0], end[0])
        miny = min(start[1], end[1])
        maxx = max(start[0], end[0])
        maxy = max(start[1], end[1])
        return goocanvas.Bounds(minx,miny,maxx,maxy)

    def do_simple_create_path(self, cr):
        # For hit testing
        start = self.get_start_anchor()
        end = self.get_end_anchor()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(self.get_edge_width())
        cr.curve_to(0.5 * (start[0]+end[0]), start[1],
            0.5 * (start[0]+end[0]), end[1], end[0], end[1])
    
    def do_simple_paint(self, cr, bounds):
        my_bounds = self.get_bounds()
        if(not boundsutils.do_intersect(my_bounds, bounds)):
            return

        my_bounds = self._get_internal_bounds()

        start = self.get_start_anchor()
        end = self.get_end_anchor()
        width = self.get_edge_width()

        if(self.is_valid()):
            scheme = self.get_color_scheme()
        else:
            scheme = self.get_invalid_color_scheme()

        cr.new_path()
        cr.move_to(start[0], start[1])
        cr.curve_to(0.5 * (start[0]+end[0]), start[1],
            0.5 * (start[0]+end[0]), end[1], end[0], end[1])
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(self.get_edge_width())
        tango.cairo_set_source(cr, scheme, tango.DARK)
        cr.stroke_preserve()
        cr.set_line_width(self.get_edge_width() - 2)

        tango.cairo_set_source(cr, scheme, tango.LIGHT)
        cr.stroke()

gobject.type_register(EdgeItem)

class EdgeModel(goocanvas.GroupModel, goocanvas.ItemModel):
    __gproperties__ = {
        'color-scheme': (str, None, None, 'Plum',
            gobject.PARAM_READWRITE),
        'invalid-color-scheme': ( str, None, None, 'Scarlet Red', 
            gobject.PARAM_READWRITE ) ,
        'graph-model': (gobject.TYPE_OBJECT, None, None,
            gobject.PARAM_READWRITE),
        'start-pad': (gobject.TYPE_OBJECT, None, None,
            gobject.PARAM_READWRITE),
        'end-pad': (gobject.TYPE_OBJECT, None, None,
            gobject.PARAM_READWRITE),
    }

    def __init__(self, graph_model, *args, **kwargs):
        self._edge_data = {
            'color-scheme': 'Butter',
            'invalid-color-scheme': 'Scarlet Red',
            'graph-model': graph_model,
            'start-pad': None,
            'end-pad': None,
        }

        goocanvas.GroupModel.__init__(self, *args, **kwargs)
    
    def is_valid(self):
        return True

    def get_graph_model(self):
        return self.get_property('graph-model')

    ## gobject methods
    def do_get_property(self, pspec):
        propnames = self._edge_data.keys()
        if(pspec.name in propnames):
            return self._edge_data[pspec.name]
        else:
            raise AttributeError('No such property: %s' % pspec.name)

    def do_set_property(self, pspec, value):
        propnames = self._edge_data.keys()
        if(pspec.name in propnames):
            self._edge_data[pspec.name] = value
            self.emit('changed', False)
        else:
            raise AttributeError('No such property: %s' % pspec.name)

        if(pspec.name in ('start-pad', 'end-pad')):
            # Tell the pad it's been connected
            value.connected_to_edge(self)

        self.notify(pspec.name)
    
    ## item model methods
    def do_create_item(self, canvas):
        item = EdgeItem()
        item.set_canvas(canvas)
        item.set_model(self)
        return item

gobject.type_register(EdgeModel)

# vim:sw=4:ts=4:autoindent
