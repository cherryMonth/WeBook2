from flask import render_template, redirect, flash, url_for, request, abort
from flask import Blueprint, current_app, send_from_directory
import os
import re
from app.main.parse import Extractor
import markdown
from app.main.models import Category, Comment
from app.main.forms import FindUser
from app.main.models import User, Information
from app import db
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from sqlalchemy import text
import json

dropdown = Blueprint("dropdown", __name__)

@dropdown.route("/get_index_page", methods=['GET', 'POST'])
def get_index_page():
    _id = int(request.args['_id'])
    tmp = Category.query.order_by(Category.update_time.desc()).order_by(Category.rate.desc()). \
        order_by(Category.collect_num.desc())
    length = len(tmp.all())
    target_page_num = 5
    page_num = int(length / target_page_num if length % target_page_num == 0 else length / target_page_num + 1)
    if _id > page_num:
        return '[]'
    hot_doc_list = tmp.paginate(_id, target_page_num, error_out=True).items
    docs_html_list = list()
    for doc in hot_doc_list:
        html = """<li id="{}" class="have-img">
                        <a class="warp-img" href="/display/{}">
                        <img class="  img-blur-done" src={} style="float:right;margin-right:37%" height=100 width=125>
                        </a>
                        <div style="margin-top: 20px;" class="container">
                            <a class="title" target="_blank" href="/display/{}">{}</a>
                            <p  class="abstract" style="cursor:pointer" onclick="window.location='/display/{}';">
                                {}
                            </p>
                            </div>
                            <div class="meta">
                            <span class="glyphicon glyphicon-send">{}</span>
                                <a target="_blank" style="margin-left: 20px" class='glyphicon glyphicon-eye-open' href="/display/{}">{}</a>
                                 <a target="_blank" style="margin-left: 10px" class='glyphicon glyphicon-comment' href="/display/{}">{}</a>
                                <span style="margin-left: 20px" class="flask-moment" data-timestamp="{}" data-format="fromNow(0)" data-refresh="0">{}</span>
                            </div>
                        </div>
                    </li>"""
        result = re.findall(r"""http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|(?:%[0-9a
        ...: -fA-F][0-9a-fA-F]))+""", doc.content, re.S)
        result = list(filter(lambda x: x.lower().endswith(('.gif)', '.jpg)', '.png)', '.jpeg)', 'webp)')), result))
        image_url = result[0][:-1] if result else "http://www.webook.mobi/display_images/purple-4163951_1280.jpg"

        exts = ['markdown.extensions.extra', 'markdown.extensions.codehilite', 'markdown.extensions.tables',
                'markdown.extensions.toc']
        ext = Extractor(1)
        content = ext.getPlainText(markdown.markdown(doc.content, extensions=exts))[:75] + "..."
        update_time = str(doc.update_time)
        comment_num = len(Comment.query.filter_by(post_id=doc.id).all())
        html = html.format(doc.id, doc.id, image_url, doc.id, doc.title, doc.id, content, \
                           doc.rate, doc.id, doc.collect_num, doc.id, comment_num, update_time, update_time)
        item = dict()
        item['html'] = html
        item['id'] = doc.id
        docs_html_list.append(item)
    return json.dumps(docs_html_list)