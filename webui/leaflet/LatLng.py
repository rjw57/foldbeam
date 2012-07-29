from __pyjamas__ import JS

class LatLng(object):
    def __init__(self, latitude, longitude, no_wrap=False):
        JS('this._lat_lng = new $wnd.L.LatLng(latitude, longitude, no_wrap);')

