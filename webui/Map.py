from pyjamas.ui.HTML import HTML
from pyjamas.ui.VerticalPanel import VerticalPanel

from leaflet.LatLng import LatLng
from leaflet.Map import Map as LeafletMap
from leaflet.TileLayer import TileLayer

from bootstrap.NavigationBar import NavigationBar

class Map(VerticalPanel):
    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)

        #navbar = NavigationBar()
        #navbar.add(HTML('<div class="brand">Name of this lovely map</div>'))
        #self.add(navbar)

        map_quest = TileLayer(
                'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
                maxZoom=18, attribution='Foo', subdomains='1234')

        map_ = LeafletMap(StyleName='map', Size=('100%', '100%'))
        map_.setView(LatLng(51.505, -0.09), 10).addLayer(map_quest)
        self.add(map_)
        self.setCellHeight(map_, '100%')
