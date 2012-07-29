import os

from tornado.ioloop import IOLoop
from tornado.web import StaticFileHandler

from foldbeam.web.restapi import new_application

if __name__ == '__main__':
    webui_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'output')
    application = new_application()
    #application.add_handlers(r'.*', [
    #        (r'(.*)', StaticFileHandler, { 'path': webui_path }),
    #])
    application.listen(8000)
    IOLoop.instance().start()
