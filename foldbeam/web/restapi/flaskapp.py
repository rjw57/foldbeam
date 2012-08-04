import json

from flask import Flask, request
import mimerender

mimerender = mimerender.FlaskMimeRender()
render_json = lambda **kwargs: json.dumps(kwargs)
resource = mimerender(default='json', json=render_json)

app = Flask(__name__)

# Add an after request handler to support CORS
def after_request(response):
    if 'Origin' in request.headers:
	response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
    return response
app.after_request(after_request)
