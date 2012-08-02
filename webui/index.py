import logging
logging.basicConfig(level=logging.INFO)

from pyjamas.ui.Button import Button as ButtonBase
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.HTML import HTML
from pyjamas import Window

from HorizontalCollapsePanel import HorizontalCollapsePanel
from Sidebar import Sidebar
from Map import Map

from client.user import User

class Application(SimplePanel):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)

        self.user = User('http://localhost:8888/user1')
        self.user.addErrorListener(self._user_error)
        self.user.addLoadedListener(self._update_user)
        self._update_user(self.user)

        self.user.get()

    def _update_user(self, user):
        if user.username is None:
            return

        user.maps.get()
        user.maps.addLoadedListener(self._update_user_maps)
        self._update_user_maps(self.user.maps)

    def _user_error(self, user, status, response):
        logging.error('Error loading user from %s: %s' % (user.get_resource_url(), status))

    def _update_user_maps(self, maps):
        if maps.items is None:
            # Map list is not yet loaded
            return

        if len(maps.items) == 0:
            logging.error('User has no maps')
            return

        m = maps.items[0]
        m.addLoadedListener(self._update_map)
        self._update_map(m)

    def _update_map(self, m):
        if m.name is None:
            # Data is not yet loaded
            return

        m.layers.get()

        sp = HorizontalPanel(Size=('100%', '100%'))

        sidebar = Sidebar()
        sidebar.setLayersCollection(m.layers)
        sp.add(sidebar)
        sp.setCellWidth(sidebar, '25%')

        map_ = Map(Size=('100%', '100%'))
        map_.set_map(m)
        sp.add(map_)

        self.setWidget(sp)

if __name__ == '__main__':
    app = Application(StyleName='top-container')
    RootPanel().add(app)
