from pyjamas.ui.Button import Button as ButtonBase
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.HTML import HTML
from pyjamas import Window

from leaflet.LatLng import LatLng
from leaflet.Map import Map
from leaflet.TileLayer import TileLayer

from HorizontalCollapsePanel import HorizontalCollapsePanel
from Sidebar import Sidebar

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

    map_quest = TileLayer(
            'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
            maxZoom=18, attribution='Foo', subdomains='1234')

    #map_ = SimplePanel(StyleName='map')
    map_ = Map(StyleName='map')
    map_.setView(LatLng(51.505, -0.09), 10).addLayer(map_quest)
    sp.add(map_)

    app.add(sp)

    root = RootPanel()
    root.add(app)
