from pyjamas.ui.Button import Button as ButtonBase
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.HTML import HTML
from pyjamas import Window

from HorizontalCollapsePanel import HorizontalCollapsePanel
from Sidebar import Sidebar
from Map import Map

class Button(ButtonBase):
    def __init__(self, *args, **kwargs):
        super(Button, self).__init__(*args, **kwargs)
        self.addStyleName('btn')

def greet(sender):
    Window.alert("Hello, AJAX!")

if __name__ == '__main__':
    app = SimplePanel(StyleName='top-container')

    sp = HorizontalPanel(Size=('100%', '100%'))

    sidebar = Sidebar()
    sp.add(sidebar)
    sp.setCellWidth(sidebar, '25%')

    map_ = Map(Size=('100%', '100%'))
    sp.add(map_)

    app.add(sp)

    root = RootPanel()
    root.add(app)
