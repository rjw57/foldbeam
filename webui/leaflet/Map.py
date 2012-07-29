from pyjamas import DOM
from pyjamas.ui import Event
from pyjamas.ui.FocusWidget import FocusWidget
from __pyjamas__ import JS

class Map(FocusWidget):
    def __init__(self, options=None, *args, **kwargs):
        element = DOM.createDiv()
        if not 'StyleName' in kwargs:
            kwargs['StyleName'] = 'leaflet-Map'
        FocusWidget.__init__(self, element, *args, **kwargs)

        map_element = DOM.createDiv()
        DOM.setStyleAttribute(map_element, 'width', '100%')
        DOM.setStyleAttribute(map_element, 'height', '100%')
        DOM.appendChild(element, map_element)
        JS('this._map = new $wnd.L.Map(map_element, pyjslib.toJSObjects(options));')

    def setView(self, center, zoom, forceReset=False):
        JS('this._map.setView(center._lat_lng, zoom, forceReset);')
        return self

    def addLayer(self, tile_layer):
        JS('this._map.addLayer(tile_layer._tile_layer);')
        return self

    def invalidateSize(self):
        JS('this._map.invalidateSize();')

    def onAttach(self):
        FocusWidget.onAttach(self)
        JS( '''
            var map = this._map;
            var onResize = function() { map.invalidateSize(); }
            onResize();
            $wnd.$(this.getElement()).resize(onResize);
            ''');

