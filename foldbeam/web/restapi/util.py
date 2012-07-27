import json

def decode_request_body(f):
    """A decorator which will attempt to interpret the request body as JSON
    and, if it succeeds, will replace the body attribute in the request object
    with the decoded body.

    """
    def wrapper(self, *args, **kwargs):
        if len(self.request.body) == 0:
            self.request.body = {}
        else:
            try:
                self.request.body = json.loads(self.request.body)
            except ValueError as e:
                # Could not decode JSON
                self.send_error(400) # Bad request
                return
        f(self, *args, **kwargs)
    return wrapper
        
def update_map(m, request):
    """Given a decoded request, update an existing map from it."""
    if 'name' in request:
        m.name = request['name']
        
def update_layer(l, request):
    """Given a decoded request, update an existing layer from it."""
    if 'name' in request:
        l.name = request['name']

