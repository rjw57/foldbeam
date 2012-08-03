import json

from flask import Flask
import mimerender

mimerender = mimerender.FlaskMimeRender()
render_json = lambda **kwargs: json.dumps(kwargs)
resource = mimerender(default='json', json=render_json)

app = Flask(__name__)
