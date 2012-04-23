from .graphcanvas import GraphModel
from .model import FoldbeamNodeModel
from foldbeam.nodes import LayerRasterNode
from foldbeam.graph import node_classes
import pygtk
import gtk
import goocanvas

class Application:
    def main_win_destroy(self, widget, data=None):
        gtk.main_quit()

    def new_canvas(self, graph_model):
        bg_color = 0xBABDB6
        graph_widget = goocanvas.Canvas()
        graph_widget.set_property('background-color-rgb', bg_color)
        graph_widget.set_property('automatic-bounds', True)
        graph_widget.set_property('integer-layout', True)
        graph_widget.set_root_item_model(graph_model)
        #graph_widget.connect('button-press-event', self._button_press)
        #graph_widget.connect('scroll-event', self._scroll_event)

        return graph_widget

    def _on_contents_changed(self, node):
        self._image_widget.queue_draw()

    def _on_edge_added(self, graph, edge):
        start = edge.get_property('start-pad')
        end = edge.get_property('end-pad')
        if hasattr(end, 'watch_pad'):
            end.watch_pad(start)

    def _on_edge_removed(self, graph, edge):
        end = edge.get_property('end-pad')
        if hasattr(end, 'set_value'):
            end.set_value(None)

    def _on_menu_destroy(self, menu):
        menu.destroy()

#    def _on_new_kernel(self, action):
#        self.new_kernel_node(*self._graph_canvas.get_pointer())

    def _on_remove_node(self, action):
        if self._remove_model is None:
            return

        node_idx = self._model.find_node(self._remove_model)

        if(node_idx >= 0):
            self._model.remove_node(node_idx)

        self._remove_model = None

    def _null_action(self, action):
        pass

    def _on_add_node(self, action):
        clsname = action.get_name()[4:]

        node_cls = [x for x in node_classes if x.__name__ == clsname][0]
        x, y = self._popup_location

        node = FoldbeamNodeModel(
            node=node_cls(),
            color_scheme = 'Sky Blue',
            x = x, y = y,
            radius_x = 6, radius_y = 6,
            width = 200, height = 70)
        self._model.add_node(node, -1)

    def _do_graph_popup(self, graph, event):
        self._popup_location = self._graph_canvas.get_pointer()
        uimanager = gtk.UIManager()

        node_actions = [
                (
                    'add-' + cls.__name__, gtk.STOCK_NEW, 'Add ' + cls.__name__, None,
                    'Add a new ' + cls.__name__ + ' node.', self._on_add_node
                )
                for cls in node_classes
        ]


        actiongroup = gtk.ActionGroup('GraphPopupActions')
        actiongroup.add_actions([
            ('quit-application', gtk.STOCK_QUIT, '_Quit', None,
             'Quit this application.', gtk.main_quit),
            ] + node_actions + [ \
            ('remove-node', gtk.STOCK_REMOVE, '_Remove Node', None,
             'Remove the node under the pointer.', self._on_remove_node),
            ])

        uimanager.insert_action_group(actiongroup)
            
        uimanager.add_ui_from_string('''
  <ui>
    <popup name="Popup">
      <menuitem action="remove-node" />
''' + '\n'.join(['<menuitem action="%s" />' % (x[0],) for x in node_actions]) + '''
      <menuitem action="quit-application" />
    </popup>
  </ui>
        ''')

        items = self._graph_canvas.get_items_at(
            self._popup_location[0], self._popup_location[1],
            True)

        if (items is not None) and (len(items) > 0):
            item = items[0].get_parent()
            if item is not None:
                model = item.get_model()
                if hasattr(model, 'is_removable') and (model.is_removable):
                    uimanager.add_ui_from_string('''
          <ui>
            <popup name="Popup">
              <separator />
              <menuitem action="remove-node" />
            </popup>
          </ui>
                    ''')
                    self._remove_model = model
 
        # Add the quit option.
        uimanager.add_ui_from_string('''
  <ui>
    <popup name="Popup">
        <separator />
        <menuitem action="quit-application" />
    </popup>
  </ui>
        ''')

        # Create the popup menu
        menu = uimanager.get_widget('/Popup')

        if event is None:
            button = 0
            event_time = gtk.get_current_event_time()
        else:
            button = event.button
            event_time = event.time

        menu.attach_to_widget(graph, None)
        menu.popup(None, None, None, button, event_time, None)

    def _on_graph_popup_menu(self, graph):
        self._do_graph_popup(graph, None)
        return True

    def _on_graph_button_press(self, graph, event):
        if (event.button == 3) and (event.type == gtk.gdk.BUTTON_PRESS):
            self._do_graph_popup(graph, event)
            return True
        return False

    def __init__(self):
        gtk.gdk.threads_init()

#        self._image_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
#        self._image_window.set_position(gtk.WIN_POS_NONE)
#        self._image_window.connect('destroy', self.main_win_destroy)
#        self._image_window.set_default_size(640, 480)
#        self._image_window.set_title('Foldbeam output')

#        image_scroller = DragScrolledWindow()
#        self._image_window.add(image_scroller)

#        self._image_widget = ImageWidget()
#        image_scroller.add(self._image_widget)

        self._graph_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self._graph_window.set_position(gtk.WIN_POS_NONE)
        self._graph_window.connect('destroy', self.main_win_destroy)
        self._graph_window.set_default_size(640, 480)
        self._graph_window.set_title('Foldbeam graph')
        
        graph_scroller = gtk.ScrolledWindow()
        self._graph_window.add(graph_scroller)

        self._model = GraphModel()
        graph_canvas = self.new_canvas(self._model)
        self._graph_canvas = graph_canvas
        graph_scroller.add(graph_canvas)
        graph_canvas.connect('popup-menu', self._on_graph_popup_menu)
        graph_canvas.connect('button-press-event', self._on_graph_button_press)
        
        self._model.connect('edge-added', self._on_edge_added)
        self._model.connect('edge-removed', self._on_edge_removed)

        self._graph_window.show_all()

    def run(self):
        gtk.main()

if __name__ == '__main__':
    app = Application()
    app.run()

# vim:sw=4:ts=4:et:autoindent

