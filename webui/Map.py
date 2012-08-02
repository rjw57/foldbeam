import logging

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

        self._map = LeafletMap(StyleName='map', Size=('100%', '100%'))
        self._map.setView(LatLng(51.505, -0.09), 0)
        self.add(self._map)
        self.setCellHeight(self._map, '100%')

    def set_map(self, m):
        m.addLoadedListener(self._update_map)
        self._update_map(m)

    def _update_map(self, m):
        if m is None or m.name is None:
            # not yet loaded
            return

        self._map.clearLayers()
        pattern = m.tms_tile_base + '{z}/{x}/{y}.png'
        logging.error(pattern)
        layer = TileLayer(pattern, tms=True)
        self._map.addLayer(layer)
