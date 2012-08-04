from .flaskapp import app, resource

from . import user, map, layer, bucket, rendering

#@app.route('/')
#@resource
#def index():
#    # FIXME: put more useful stuff here
#    return { }

wsgi_application = app.wsgi_app
