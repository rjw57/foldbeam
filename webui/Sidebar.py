from pyjamas import DOM
from pyjamas.ui.Button import Button
from pyjamas.ui.HTML import HTML
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Tree import Tree
from pyjamas.ui.TreeItem import TreeItem
from pyjamas.ui.VerticalPanel import VerticalPanel

from bootstrap.NavigationBar import NavigationBar

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
        for x in ['fooble', 'biggle', 'booof']:
            item = TreeItem(Text='Hello, ' + x)
            self._tree.addItem(item)
        self.add(self._tree)

class Sidebar(SimplePanel):
    def __init__(self, *args, **kwargs):
        super(Sidebar, self).__init__(*args, **kwargs)

        if self.getStylePrimaryName() is None:
            self.addStyleName('sidebar')

        vp = VerticalPanel(Size=('100%', '100%'))

        layers = LayersPanel(Width='100%')
        vp.add(layers)

        self.add(vp)
