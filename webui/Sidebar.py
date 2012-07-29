from pyjamas import DOM
from pyjamas.ui.DragWidget import DragWidget
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.HTML import HTML
from pyjamas.ui.Label import Label
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.ToggleButton import ToggleButton
from pyjamas.ui.Tree import Tree
from pyjamas.ui.TreeItem import TreeItem
from pyjamas.ui.VerticalPanel import VerticalPanel

class Layer(DragWidget, SimplePanel):
    def __init__(self, *args, **kwargs):
        SimplePanel.__init__(self, *args, **kwargs)
        self.add(Label('foo'))
#        self.setText('Hello there!')
        DragWidget.__init__(self, *args, **kwargs)

class Sidebar(SimplePanel):
    def __init__(self, *args, **kwargs):
        super(Sidebar, self).__init__(*args, **kwargs)

        if self.getStylePrimaryName() is None:
            self.addStyleName('sidebar')

        hp = FlowPanel(StyleName=self.getStylePrimaryName() + '-elements')

        collapse = ToggleButton(StyleName=self.getStylePrimaryName() + '-collapse')
        collapse.addClickListener(self._sync_collapse)
        self._sync_collapse(collapse)
        hp.add(collapse)

        cp = FlowPanel(StyleName=self.getStylePrimaryName() + '-content')

        layers = Tree(StyleName='layers-tree')
        layers.addItem(TreeItem(Widget=Layer()))
        layers.addItem(TreeItem(Widget=Layer()))
        layers.addItem(TreeItem(Widget=Layer()))
        layers.addItem(TreeItem(Widget=Layer()))
        layers.getItem(2).addItem(TreeItem(Widget=Layer()))
    
        cp.add(HTML('<h6>Layers</h6>'))
        cp.add(layers)
        cp.add(HTML('<h6>Library</h6>'))

        hp.add(cp)

        self.add(hp)

    def _sync_collapse(self, checkbox):
        if checkbox.isDown():
            self.addStyleDependentName('collapsed')
            self.removeStyleDependentName('expanded')
        else:
            self.removeStyleDependentName('collapsed')
            self.addStyleDependentName('expanded')
