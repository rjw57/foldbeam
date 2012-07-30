import logging

from pyjamas import DOM
from pyjamas.HTTPRequest import HTTPRequest
from pyjamas.ui.Button import Button
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Label import Label
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Tree import Tree
from pyjamas.ui.TreeItem import TreeItem
from pyjamas.ui.VerticalPanel import VerticalPanel

from bootstrap.NavigationBar import NavigationBar

class LayerLabel(SimplePanel):
    def __init__(self, layer, **kwargs):
        super(LayerLabel, self).__init__(**kwargs)

        self.setWidget(Label('Loading...'))
        layer.addLoadedListener(self._update)
        self._update(layer)

    def _update(self, layer):
        label = Label(layer.name)
        self.setWidget(label)

class LayersPanel(VerticalPanel):
    def __init__(self, *args, **kwargs):
        super(LayersPanel, self).__init__(*args, **kwargs)
        navbar = NavigationBar()
        navbar.add(HTML('<div class="brand">Layers</div>'))

        b = Button('Edit', StyleName='btn')
        b.addStyleName('btn-inverse')
        b.addStyleName('pull-right')
        navbar.add(b)

        self.add(navbar)

        self._tree = Tree()
        self.add(self._tree)

    def setLayersCollection(self, layers):
        layers.addLoadedListener(self._update_layers)
        self._update_layers(layers)

    def _update_layers(self, layers):
        self._tree.clear()

        if layers.items is None:
            # not yet loaded
            return

        for l in layers.items:
            item = TreeItem(Widget=LayerLabel(l))
            self._tree.addItem(item)

class Sidebar(SimplePanel):
    def __init__(self, *args, **kwargs):
        super(Sidebar, self).__init__(*args, **kwargs)

        if self.getStylePrimaryName() is None:
            self.addStyleName('sidebar')

        vp = VerticalPanel(Size=('100%', '100%'))
        self._layers_panel = LayersPanel(Width='100%')
        vp.add(self._layers_panel)
        self.setWidget(vp)

    def setLayersCollection(self, layers):
        self._layers_panel.setLayersCollection(layers)


