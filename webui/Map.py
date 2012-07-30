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
        self._map.setView(LatLng(51.505, -0.09), 10)
        self.add(self._map)
        self.setCellHeight(self._map, '100%')

    def set_layer_collection(self, layers):
        layers.addLoadedListener(self._update_layer_collection)
        self._update_layer_collection(layers)

    def _update_layer_collection(self, layers):
        if layers.items is None:
            # not yet loaded
            return

        self._map.clearLayers()

        for layer in layers.items:
            if layer.name is None:
                layer.addLoadedListener(lambda l: self._update_layer_collection(layers))
                continue

            kwargs = {}
            if 'subdomains' in layer.tiles:
                kwargs['subdomains'] = layer.tiles['subdomains']
            tile_layer = TileLayer(layer.tiles['pattern'], **kwargs)
            self._map.addLayer(tile_layer)
