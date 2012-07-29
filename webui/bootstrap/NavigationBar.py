from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.SimplePanel import SimplePanel

class NavigationBar(SimplePanel):
    def __init__(self, *args, **kwargs):
        super(NavigationBar, self).__init__(*args, **kwargs)

        navbar = SimplePanel(StyleName="navbar navbar-fixed")
        navbar_inner = SimplePanel(StyleName="navbar-inner")

        self._navbar_container = FlowPanel()

        navbar_inner.add(self._navbar_container)
        navbar.add(navbar_inner)
        SimplePanel.add(self, navbar)

    def add(self, widget):
        self._navbar_container.add(widget)
