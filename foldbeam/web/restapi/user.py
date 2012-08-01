from foldbeam.web import model

from .base import BaseHandler
from .util import decode_request_body

class UserHandler(BaseHandler):
    def write_user_resource(self, user):
        self.write(self.user_resource(user))

    def user_resource(self, user):
        return {
            'username': user.username,
            'resources': {
                'map_collection': {
                    'url': self.map_collection_url(user),
                },
                'layer_collection': {
                    'url': self.layer_collection_url(user),
                },
                'bucket_collection': {
                    'url': self.bucket_collection_url(user),
                },
            },
        }

    def get(self, username):
        user = self.get_user_or_404(username)
        if user is None:
            return
        self.write_user_resource(user)

    @decode_request_body
    def put(self, username):
        # This will replace the one currently in the DB
        user = model.User(username)
        user.save()

        self.set_status(201)
        self.set_header('Location', self.user_url(user))
        self.write({ 'url': self.user_url(user) })
