import tango
import boundsutils
import cairoutils
import goocanvas
import gobject
import gtk
import tangocanvas
import cairo
import math
import random
import resizegadget
import simple
import pango
import padgadget
import edge

class NodeItem(goocanvas.Group, simple.SimpleItem, goocanvas.Item):
    def __init__(self, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)

        ## a flag for indicating if we need an update
        self._needs_update = True

        self._node_data = {
            'node-title': 'Node',
            'x': 0.0, 'y': 0.0, 'width': 100.0, 'height': 100.0,
            'radius-x': 0.0, 'radius-y': 0.0,
            'color-scheme': 'Plum',
            'pads': [],
        }

        self._background_rect = NodeItemFrame( \
            parent = self, x = 0.0, y = 0.0,
            width = 200.0, height = 30.0)

        self._graph_item = None

        # make the background item draggable
        self._dragging_frame = False
        self._background_rect.connect("motion_notify_event", 
            self._on_frame_motion_notify)
        self._background_rect.connect("button_press_event", 
            self._on_frame_button_press)
        self._background_rect.connect("button_release_event",
            self._on_frame_button_release)

        # Add a resize gadget item child
        self._dragging_resize_gadget = False
        self._resize_gadget = resizegadget.ResizeGadget( parent = self,
            orientation = resizegadget.SE, x = 0.0, y = 0.0 )
        self._resize_gadget.connect("motion_notify_event", 
            self._on_resize_gadget_motion_notify)
        self._resize_gadget.connect("button_press_event", 
            self._on_resize_gadget_button_press)
        self._resize_gadget.connect("button_release_event",
            self._on_resize_gadget_button_release)
        self._resize_gadget_size = 15

        self._ui_widget = None

        self._pad_table = None
        self._dragging_pad_gadget = False
        self._update_pad_table()
    
    def get_graph_item(self):
        return self._graph_item

    def set_graph_item(self, graph):
        self._graph_item = graph
        self._update_pad_table()

    def _update_pad_table(self):
        if(self._pad_table != None):
            self.remove_child(self.find_child(self._pad_table))
            self._pad_table = None

        self._pad_table = goocanvas.Table(parent = self, row_spacing = 4.0)
        self._pad_labels = []
        self._pad_models = []
        self._pad_gadgets = []
        self._default_pad_size = 13.0

        model = self.get_model()
        if(model == None):
            return

        n_output_pads = model.get_n_output_pads()
        total_n_pads = n_output_pads + model.get_n_input_pads()

        row_idx = 0
        for pad_idx in range(total_n_pads):
            if(pad_idx < n_output_pads):
                xalign = 1.0
                labelcolumn = 1
                padcolumn = 2
                padorient = tango.RIGHT
                ellip = pango.ELLIPSIZE_START
                pad_model = model.get_output_pad(pad_idx)
            else:
                xalign = 0.0
                padcolumn = 0
                labelcolumn = 1
                padorient = tango.LEFT
                ellip = pango.ELLIPSIZE_END
                pad_model = model.get_input_pad(pad_idx - n_output_pads)

            self._pad_models.append(pad_model)

            # register our interest in the pad
            pad_model.connect('changed', self._on_pad_changed)

            # Create the label
            pad_label = goocanvas.Text(parent=self._pad_table, 
                text=pad_model.get_property('label'),
                pointer_events=goocanvas.EVENTS_NONE,
                ellipsize=ellip,
                font='Sans 10',
                x=0.0, y=0.0)
            self._pad_labels.append(pad_label)
            self._pad_table.set_child_properties(pad_label, \
                row = row_idx, column = labelcolumn,
                x_expand = True, 
                left_padding = 4.0, right_padding = 4.0,
                x_shrink = True, x_align = xalign)

            # Create tha pad itself
            pad_gadget = padgadget.PadGadget(parent=self._pad_table, 
                x=0.0, y=0.0, 
                width=self._default_pad_size,
                height=self._default_pad_size,
                pad_size=self._default_pad_size,
                orientation=padorient,
                pointer_events = goocanvas.EVENTS_ALL)
            pad_gadget.connect("motion_notify_event", 
                self._on_pad_gadget_motion_notify)
            pad_gadget.connect("button_press_event", 
                self._on_pad_gadget_button_press)
            pad_gadget.connect("button_release_event",
                self._on_pad_gadget_button_release)
            self._pad_gadgets.append(pad_gadget)
            self._pad_table.set_child_properties(pad_gadget, \
                row = row_idx, column = padcolumn, 
                x_shrink = False, x_expand = False, x_fill = False)

            pad_gadget.set_pad_model(pad_model)

            row_idx += 1

        if(self._ui_widget != None):
            widget_item = goocanvas.Widget(parent = self._pad_table,
                widget = self._ui_widget)
            self._pad_table.set_child_properties(widget_item, 
                row = row_idx, column = 0,
                columns = 3, x_fill = True, y_fill = True,
                y_expand = True,
                left_padding = 6.0, right_padding = 6.0)
            self._ui_widget.show_all()

    def _on_pad_changed(self, model, recompute):
        self._update_pad_table()
        self._needs_update = True
        self.changed(True)
    
    def do_update(self, entire_tree, cr):
        if(not self._needs_update):
            out_bounds = goocanvas.Bounds()
            goocanvas.Group.do_update(self, entire_tree, cr, out_bounds)
            return out_bounds

        ## attempt to set the width and height of the pad table to automatic
        content_rect = self._background_rect.get_content_area_bounds()
        self._pad_table.set_property('width', -1)
        self._pad_table.set_property('height', -1)
        try:
            self._pad_table.update(entire_tree, cr, goocanvas.Bounds())
        except:
            self._pad_table.update(entire_tree, cr)

        ## get the requested bounds of the pad table
        pad_req = goocanvas.Bounds()
        try:
            self._pad_table.get_requested_area(cr, pad_req)
        except:
            pad_req = self._pad_table.get_requested_area(cr)

        ## and hence the minimum comfortable size of the node
        comfortable_bounds = self._background_rect. \
            get_bounds_for_desired_content_bounds(cr, pad_req)
        comfortable_size = boundsutils.get_size(comfortable_bounds)

        ## see if we're set to use the automagic width and height
        if(self._node_data['width'] < 0.0):
            self._node_data['width'] = comfortable_size[0]
        if(self._node_data['height'] < 0.0):
            self._node_data['height'] = comfortable_size[1]

        ## find the minimum width and height for the node frame.
        minimum_bounds = self._background_rect. \
            get_bounds_for_desired_content_bounds(cr, goocanvas.Bounds(0,0,0,0))
        (minimum_width, minimum_height) = boundsutils.get_size(minimum_bounds)

        ## update the requested width and height.
        self._node_data['width'] = max(self._node_data['width'], minimum_width)
        self._node_data['height'] = max(self._node_data['height'], minimum_height)

        ## update the minimum bounds
        minimum_bounds = self._background_rect. \
            get_bounds_for_desired_content_bounds(cr, pad_req)
        (minimum_width, minimum_height) = boundsutils.get_size(minimum_bounds)

        ## add in the resize gadget and the vertical padding
        vertical_padding = 6.0
        minimum_height += math.ceil(0.2 * self._resize_gadget_size) + \
            2.0*vertical_padding

        ## update the requested height ignoring the minimum width
        ## because the pads ellipsize.
        self._node_data['height'] = max(self._node_data['height'], 
            minimum_height)

        # Make width, height and position integer
        self._node_data['width'] = math.ceil(self._node_data['width'])
        self._node_data['height'] = math.ceil(self._node_data['height'])
        self._node_data['x'] = math.ceil(self._node_data['x'])
        self._node_data['y'] = math.ceil(self._node_data['y'])

        ## update all the properties for the background.
        propnames = ('width', 'height', 'radius-x',
            'radius-y', 'color-scheme', 'node-title')
        for name in propnames:
            self._background_rect.set_property(name, self._node_data[name])

        ## update the translation of each child
        for child_idx in range(self.get_n_children()):
            child = self.get_child(child_idx)
            child.set_simple_transform( self._node_data['x'],
                self._node_data['y'], 1.0, 0.0 )
            try:
                child.update(entire_tree, cr, goocanvas.Bounds())
            except:
                child.update(entire_tree, cr)

        ## get the bounds of the content area
        content_rect = self._background_rect.get_content_area_bounds()

        ## update the position and size of the pad table. It extends
        ## horizontally to the edge of the item.
        self._pad_table.translate(-1, content_rect.y1 + vertical_padding)
        self._pad_table.set_property('width', self._node_data['width']+2)
        self._pad_table.set_property('height',
            content_rect.y2 - content_rect.y1 - self._resize_gadget_size)
        try:
            self._pad_table.update(entire_tree, cr, goocanvas.Bounds())
        except:
            self._pad_table.update(entire_tree, cr)

        ## now update each pad gadget's anchor location if there is
        ## a parent graph item
        graph_item = self.get_graph_item()
        model = self.get_model()

        if((graph_item != None) and (model != None)):
            for pad_gadget in self._pad_gadgets:
                pad_anchor = pad_gadget.get_pad_anchor()
                canvas_space_anchor = self.get_canvas().\
                    convert_from_item_space(pad_gadget, *pad_anchor)
                graph_item.set_pad_anchor(pad_gadget.get_pad_model(),
                    *canvas_space_anchor)

        ## Put the resize gadget in the lower-right
        self._resize_gadget.translate(
            content_rect.x2 - self._resize_gadget_size - 1,
            content_rect.y2 - self._resize_gadget_size - 1)
        self._resize_gadget.set_property('width', self._resize_gadget_size)
        self._resize_gadget.set_property('height', self._resize_gadget_size)
        self._resize_gadget.set_color_scheme( self._node_data['color-scheme'] )

        ## update the fill colour of each pad label
        label_color = tango.get_color_hex_string_rgb( 
            self._node_data['color-scheme'],
            tango.MEDIUM_CONTRAST)
        for label in self._pad_labels:
            label.set_property('fill_color', label_color)

        for gadget in self._pad_gadgets:
            gadget.set_color_scheme( self._node_data['color-scheme'] )

        out_bounds = goocanvas.Bounds()
        goocanvas.Group.do_update(self, entire_tree, cr, out_bounds)
        self._needs_update = False

        return out_bounds
    
    def _get_pad_at(self, x, y):
        items = self.get_canvas().get_items_at(x,y,False)
        pad_item = None
        if(items != None):
            for item in items:
                if(isinstance(item, padgadget.PadGadget)):
                    pad_item = item
        return pad_item

    ## event handlers
    def _on_pad_gadget_motion_notify(self, item, target, event):
        if((self._dragging_pad_gadget == True) and 
          (event.state & gtk.gdk.BUTTON1_MASK)):
            root_item = self.get_canvas().get_root_item()
            event_point = self.get_canvas().\
                convert_from_item_space(target, event.x, event.y)
            self._temporary_edge_item.set_end_anchor(*event_point)
            self._temporary_edge_item.ensure_updated()
            root_item.ensure_updated()
        return True
    
    def _on_pad_gadget_button_press(self, item, target, event):
        if(event.button == 1): # left button
            # check target is an output pad
            pad_model = target.get_pad_model()
            pad_type = pad_model.get_property('type')

            if(pad_model == None):
                return

            # If this is an input pad, see if it is connected already
            if((pad_type == padgadget.INPUT) and 
                (pad_model.get_n_connected_edges() == 0)):
                return

            root_item = self.get_canvas().get_root_item()
            pad_anchor = target.get_pad_anchor()
            event_point = self.get_canvas().\
                convert_from_item_space(target, event.x, event.y)
            canvas_space_anchor = self.get_canvas().\
                convert_from_item_space(target, *pad_anchor)
            self._temporary_edge_item = edge.EdgeItem( \
                parent = root_item,
                pointer_events = goocanvas.EVENTS_NONE,
                edge_width = self._default_pad_size - 4.0) 

            if(pad_type == padgadget.INPUT):
                connected_edge_model = pad_model.get_connected_edges()[0]
                graph_model = self.get_model().get_graph_model()
                connected_edge_model_idx = graph_model.find_edge(connected_edge_model)
                graph_model.remove_edge(connected_edge_model_idx)

                start_pad = connected_edge_model.get_property('start-pad')
                start_anchor = self.get_graph_item().get_pad_anchor(start_pad)
                self._temporary_edge_item.set_start_anchor(*start_anchor)
                self._temporary_edge_item.set_end_anchor(*event_point)

                ## record what the start pad is
                self._edge_start_pad_model = start_pad
            else:
                self._temporary_edge_item.set_start_anchor(*canvas_space_anchor)
                self._temporary_edge_item.set_end_anchor(*event_point)

                ## record what the start pad is
                self._edge_start_pad_model = target.get_pad_model()

            root_item.ensure_updated()

            fleur = gtk.gdk.Cursor (gtk.gdk.FLEUR)
            canvas = item.get_canvas ()
            canvas.pointer_grab(item,
                gtk.gdk.POINTER_MOTION_MASK | 
                    gtk.gdk.BUTTON_RELEASE_MASK,
                fleur, event.time)
            self._dragging_pad_gadget = True
        return True

    def _on_pad_gadget_button_release(self, item, target, event):
        if(not self._dragging_pad_gadget):
            return

        canvas = item.get_canvas ()
        canvas.pointer_ungrab(item, event.time)
        self._dragging_pad_gadget = False

        # see if we have any pad gadgets under the mouse
        event_point = self.get_canvas().\
            convert_from_item_space(target, event.x, event.y)
        mouse_pad = self._get_pad_at(*event_point)

        # see if the edge is valid (and hence should be 
        # added to the model, should we have one).
        model = self.get_model()
        graph_model = model.get_graph_model()
        if((model != None) and (self._temporary_edge_item.is_valid())):
            edge_model = model.create_edge_model(
                self._edge_start_pad_model, mouse_pad.get_pad_model())

        # Remove the temporary edge
        temp_parent = self._temporary_edge_item.get_parent()
        idx = temp_parent.find_child(self._temporary_edge_item)
        temp_parent.remove_child(idx)
        self._temporary_edge_item = None

    def _on_frame_motion_notify(self, item, target, event):
        if((self._dragging_frame == True) and 
           (event.state & gtk.gdk.BUTTON1_MASK)):
            event_point = self.get_canvas().\
                convert_from_item_space(self._resize_gadget, event.x, event.y)
            delta_x = event_point[0] - self._drag_point[0]
            delta_y = event_point[1] - self._drag_point[1]
            new_x = self._old_loc[0] + delta_x
            new_y = self._old_loc[1] + delta_y
            self.get_model().set_property('x', new_x)
            self.get_model().set_property('y', new_y)
            self._needs_update = True
            self.ensure_updated()
        return True
    
    def _on_frame_button_press(self, item, target, event):
        if(event.button == 1): # left button
            self._drag_point = self.get_canvas().\
                convert_from_item_space(self._resize_gadget, event.x, event.y)
            self._old_loc = ( self._node_data['x'], self._node_data['y'] )
            fleur = gtk.gdk.Cursor (gtk.gdk.FLEUR)
            canvas = item.get_canvas ()
            canvas.pointer_grab(item,
                gtk.gdk.POINTER_MOTION_MASK | 
                    gtk.gdk.BUTTON_RELEASE_MASK,
                fleur, event.time)
            self._dragging_frame = True

        return True

    def _on_frame_button_release(self, item, target, event):
        canvas = item.get_canvas ()
        canvas.pointer_ungrab(item, event.time)
        self._dragging_frame = False
    
    def _on_resize_gadget_motion_notify(self, item, target, event):
        if((self._dragging_resize_gadget == True) and 
           (event.state & gtk.gdk.BUTTON1_MASK)):
            event_point = self.get_canvas().\
                convert_from_item_space(self._resize_gadget, event.x, event.y)
            delta_x = event_point[0] - self._drag_point[0]
            delta_y = event_point[1] - self._drag_point[1]
            new_width = max(self._resize_gadget_size,
                self._old_size[0] + delta_x)
            new_height = max(self._resize_gadget_size,
                self._old_size[1] + delta_y)
            self.get_model().set_property('width', new_width)
            self.get_model().set_property('height', new_height)
            self._needs_update = True
            self.ensure_updated()
        return True
    
    def _on_resize_gadget_button_press(self, item, target, event):
        if(event.button == 1): # left button
            self._drag_point = self.get_canvas().\
                convert_from_item_space(self._resize_gadget, event.x, event.y)
            self._old_size = ( self._node_data['width'], self._node_data['height'] )
            fleur = gtk.gdk.Cursor (gtk.gdk.BOTTOM_RIGHT_CORNER)
            canvas = item.get_canvas ()
            canvas.pointer_grab(item,
                gtk.gdk.POINTER_MOTION_MASK | 
                    gtk.gdk.BUTTON_RELEASE_MASK,
                fleur, event.time)
            self._dragging_resize_gadget = True
        return True

    def _on_resize_gadget_button_release(self, item, target, event):
        canvas = item.get_canvas ()
        canvas.pointer_ungrab(item, event.time)
        self._dragging_resize_gadget = False

    def _on_model_changed(self, model, recompute_bounds):
        self._needs_update = True
        self.changed(recompute_bounds)
    
    def _on_pads_changed(self, model):
        self._update_pad_table()
        self._needs_update = True
        self.changed(True)
    
    ## simple item methods
    def set_model(self, model):
        goocanvas.Group.set_model(self, model)

        # so nefarious
        self._node_data = model._node_data

        # Create our UI widget
        self._ui_widget = model.create_widget()

        model.connect('changed', self._on_model_changed)
        model.connect('pads-changed', self._on_pads_changed)
        self._update_pad_table()
        self._on_model_changed(model, True)

gobject.type_register(NodeItem)

class NodeItemFrame(tangocanvas.TangoRectItem, goocanvas.Item):
    __gproperties__ = {
        'node-title':   (str, None, None, 'Node',
            gobject.PARAM_READWRITE),
    }

    def __init__(self, *args, **kwargs):
        self._node_data = {
            'node-title': 'Node',
        }
        self._font_size = 16
        self._content_bounds = goocanvas.Bounds()

        # Initialise the remaining parts of the item
        tangocanvas.TangoRectItem.__init__(self, *args, **kwargs)
    
    def get_node_title(self):
        return self.get_property('node-title')

    def set_node_title(self, title):
        self.set_property('node-title', title)

    def get_content_area_bounds(self):
        return self._content_bounds

    ## item methods
    def get_bounds_for_desired_content_bounds(self, cr, content_bounds):
        cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(self._font_size)
        extents = cr.text_extents(self.get_node_title())
        font_width = math.ceil(extents[2])
        font_height = math.ceil(extents[3])
        font_padding = math.ceil(0.5 * font_height)
        y = font_height + font_padding
        y += font_padding + 1.5
        y = math.ceil(y)
        bounds = goocanvas.Bounds()
        bounds.x1 = content_bounds.x1 - 3.0
        bounds.y1 = content_bounds.y1 - 3.0 - y
        width = max(content_bounds.x2-content_bounds.x1, font_width + 20.0)
        bounds.x2 = bounds.x1 + width + 6.0
        bounds.y2 = content_bounds.y2 + 3.0
        return bounds
    
    ## gobject methods
    def do_get_property(self, pspec):
        if(pspec.name == 'node-title'):
            return self._node_data['node-title']
        else:
            return tangocanvas.TangoRectItem.do_get_property(self, pspec)   

    def do_set_property(self, pspec, value):
        if(pspec.name == 'node-title'):
            self._node_data['node-title'] = value
            self.request_update()
            self.notify(pspec.name)
        else:
            tangocanvas.TangoRectItem.do_set_property(self, pspec, value)
    
    ## simple item methods
    def set_model(self, model):
        tangocanvas.TangoRectItem.set_model(self, model)

        # so nefarious
        self._node_data = model._node_data

    def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
        return tangocanvas.TangoRectItem.do_simple_is_item_at(self, x, y,
            cr, is_pointer_event)

    def do_simple_update(self, cr):
        tangocanvas.TangoRectItem.do_simple_update(self, cr)

        # Calculate the content area bounds
        int_bounds = self.get_interior_bounds()
        ext_bounds = self.get_bounds()
        cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(self._font_size)
        extents = cr.text_extents(self.get_node_title())
        font_height = math.ceil(extents[3])
        font_padding = math.ceil(0.5 * font_height)

        y = int_bounds.y1 + font_height + font_padding
        y += font_padding + 1.5
        y = math.ceil(y)

        self._content_bounds = goocanvas.Bounds(
            int_bounds.x1, y,
            int_bounds.x2, int_bounds.y2)

    def do_simple_create_path(self, cr):
        tangocanvas.TangoRectItem.do_simple_create_path(self, cr)
    
    def do_simple_paint(self, cr, bounds):
        my_bounds = self.get_bounds()
        if(not boundsutils.do_intersect(my_bounds, bounds)):
            return

        tangocanvas.TangoRectItem.do_simple_paint(self, cr, bounds)

        scheme = self.get_color_scheme()

        # Add our own decoration
        int_bounds = self.get_interior_bounds()

        cr.select_font_face('Sans', cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(self._font_size)

        # Draw the node title
        extents = cr.text_extents(self.get_node_title())
        font_height = math.ceil(extents[3])
        font_padding = math.ceil(0.5 * font_height)

        y = int_bounds.y1 + font_height + font_padding
        cr.move_to( \
            math.floor(0.5*(int_bounds.x1+int_bounds.x2-extents[2])),
            y)
        tango.cairo_set_source(cr, scheme, tango.DARK_CONTRAST)
        cr.show_text(self.get_node_title())

        # Draw a separator
        y += font_padding + 0.5
        cr.set_line_width(1.0)
        cr.move_to( int_bounds.x1 + 5.5, y )
        cr.line_to( int_bounds.x2 - 5.5, y )
        tango.cairo_set_source(cr, scheme, tango.DARK)
        cr.stroke()

        y += 1.0
        cr.move_to( int_bounds.x1 + 5.5, y )
        cr.line_to( int_bounds.x2 - 5.5, y )
        tango.cairo_set_source(cr, scheme, tango.LIGHT)
        cr.stroke()

        node_bounds = boundsutils.align_to_integer_boundary( \
            self.get_bounds())

        content_bounds = boundsutils.inset( \
            self.get_content_area_bounds(), 2.0, 2.0)

gobject.type_register(NodeItemFrame)

class NodeModel(goocanvas.GroupModel, goocanvas.ItemModel):
    __gproperties__ = {
        'node-title':   (str, None, None, 'Node',
            gobject.PARAM_READWRITE),
        'x': (gobject.TYPE_DOUBLE, None, None, 
            -gobject.G_MAXDOUBLE, gobject.G_MAXFLOAT,
            0.0, gobject.PARAM_READWRITE),
        'y': (gobject.TYPE_DOUBLE, None, None,
            -gobject.G_MAXDOUBLE, gobject.G_MAXFLOAT,
            0.0, gobject.PARAM_READWRITE),
        'width': (gobject.TYPE_DOUBLE, None, None, 
            -1, gobject.G_MAXDOUBLE,
            100.0, gobject.PARAM_READWRITE),
        'height': (gobject.TYPE_DOUBLE, None, None,
            -1, gobject.G_MAXDOUBLE,
            100.0, gobject.PARAM_READWRITE),
        'radius-x': (gobject.TYPE_DOUBLE, None, None, 
            0.0, gobject.G_MAXDOUBLE,
            0.0, gobject.PARAM_READWRITE),
        'radius-y': (gobject.TYPE_DOUBLE, None, None,
            0.0, gobject.G_MAXDOUBLE,
            0.0, gobject.PARAM_READWRITE),
        'color-scheme': (str, None, None, 'Plum',
            gobject.PARAM_READWRITE),
        'graph-model': (gobject.TYPE_OBJECT, None, None,
            gobject.PARAM_READWRITE),
    }

    __gsignals__ = {
        'pads-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, *args, **kwargs):
        self._node_data = {
            'node-title': 'Node',
            'x': 0.0, 'y': 0.0, 'width': 100.0, 'height': 100.0,
            'radius-x': 0.0, 'radius-y': 0.0,
            'color-scheme': 'Plum',
            'graph-model': None,
        }

        goocanvas.GroupModel.__init__(self, *args, **kwargs)
    
    ## edge factory method
    def create_edge_model(self, start_pad, end_pad):
        return edge.EdgeModel(self.get_graph_model(),
            parent = self.get_graph_model(),
            start_pad = start_pad, end_pad = end_pad)

    ## widget creation
    def create_widget(self):
        return None

    ## notify listeners that pad configuration has changed
    def pads_changed(self):
        self.emit('pads-changed')
    
    ## pad query methods
    def get_n_output_pads(self):
        ''' return the number of output pads this node has '''
        return 0
    
    def get_output_pad(self, idx):
        ''' return the padgadget.PadModel object drescribing the idx'th output pad. '''
        return None

    def get_n_input_pads(self):
        ''' return the number of input pads this node has '''
        return 0
    
    def get_input_pad(self, idx):
        ''' return the padgadget.PadModel object drescribing the idx'th input pad. '''
        return None

    def get_graph_model(self):
        return self.get_property('graph-model')

    def set_graph_model(self, value):
        self.set_property('graph-model', value)
    
    ## gobject methods
    def do_get_property(self, pspec):
        propnames = self._node_data.keys()
        if(pspec.name in propnames):
            return self._node_data[pspec.name]
        else:
            raise AttributeError('No such property: %s' % pspec.name)

    def do_set_property(self, pspec, value):
        propnames = self._node_data.keys()
        if(pspec.name in propnames):
            self._node_data[pspec.name] = value
            self.emit('changed', True)
            self.notify(pspec.name)
        else:
            raise AttributeError('No such property: %s' % pspec.name)
    
    ## item model methods
    def do_create_item(self, canvas):
        item = NodeItem()
        item.set_model(self)
        item.set_canvas(canvas)
        return item

gobject.type_register(NodeModel)

# vim:sw=4:ts=4:autoindent
