# coding=utf-8

from twisted.internet import reactor
from twisted.web import server
from twisted.web.wsgi import WSGIResource
from twisted.python import log
from app.main.hbase import HBaseDBConnection
import sys
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
from flask_login import current_user
from flask import redirect, url_for, request
from app import create_app, db
from app.main.models import User, Category, Comment, Topic, Favorite

import sys

reload(sys)
sys.setdefaultencoding('utf8')

log.startLogging(sys.stdout)
app = create_app('default')
admin = Admin(app)


class MyModelView(ModelView):

    def is_accessible(self):
        if current_user.is_authenticated and current_user.role_id > 1:
            return True
        return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access

        return redirect(url_for('auth.login', next=request.url))


admin.add_view(MyModelView(Topic, db.session, name="topic_manager"))
admin.add_view(MyModelView(Category, db.session, name='category_manager'))
admin.add_view(MyModelView(Comment, db.session, name='comment_manager'))
admin.add_view(MyModelView(User, db.session, name='user_manager'))

with app.app_context():
    db.create_all()

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
site = server.Site(resource)
reactor.listenTCP(int(os.environ.get("ServerConfig")), site)
reactor.run()
