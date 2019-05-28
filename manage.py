from twisted.internet import reactor
from twisted.web import server
from twisted.web.wsgi import WSGIResource
from twisted.python import log
import sys
import os
from app import create_app, db


log.startLogging(sys.stdout)
app = create_app('default')

with app.app_context():
    db.create_all()

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
site = server.Site(resource)
reactor.listenTCP(int(os.environ.get("ServerConfig")), site)
reactor.run()