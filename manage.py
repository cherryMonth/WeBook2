# coding=utf-8

from tornado.options import options, define
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
from flask_login import current_user
from flask import redirect, url_for, request
from app import create_app, db
from app.main.models import User, Category, Comment, Topic

import sys

reload(sys)
sys.setdefaultencoding('utf8')

define(name="port", default=os.environ.get("ServerConfig"), type=int)

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
    category = Category.query.filter_by(id>0)

# from flask_migrate import Migrate,MigrateCommand
# migrate = Migrate(app,db)
# manager = Manager(app)
# manager.add_command('db',MigrateCommand) #添加db 命令（runserver的用法）

print ('Server running on http://localhost:%s' % options.port)
http_server = HTTPServer(WSGIContainer(app))
http_server.listen(options.port)
IOLoop.instance().start()
