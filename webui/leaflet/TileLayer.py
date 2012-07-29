from __pyjamas__ import JS

class TileLayer(object):
    def __init__(self, url_template, *args, **kwargs):
        JS('this._tile_layer = new $wnd.L.TileLayer(url_template, pyjslib.toJSObjects(kwargs));')

