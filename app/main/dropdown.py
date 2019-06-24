# coding=utf-8

from flask import request
from flask import Blueprint
import pickle
from flask_login import current_user
import re
from app.main.parse import Extractor
import random
import requests
import markdown
from sqlalchemy.sql import func
from app.main.models import Category, Comment
from app.main.models import User
import json

dropdown = Blueprint("dropdown", __name__)

algo = pickle.load(open('model.pkl', 'rb'))


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
        html = u"""<li id="{}" class="have-img">
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
        result = re.findall(r"""http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|(?:%[0-9a-fA-F][0-9a-fA-F]))+""", doc.content,
                            re.S)
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


@dropdown.route("/get_author_list", methods=['GET', 'POST'])
def get_author_list():

    user = str(current_user.id)
    # 取出来对应的内部user id => to_inner_uid
    playlist_inner_id = algo.trainset.to_inner_uid(user)
    print("内部id", playlist_inner_id)

    playlist_neighbors = algo.get_neighbors(playlist_inner_id, k=100)

    author_id_list = random.sample(playlist_neighbors, 3)
    # to_raw_uid映射回去
    playlist_neighbors = (algo.trainset.to_raw_uid(inner_id)
                          for inner_id in author_id_list)

    key = [User.query.filter_by(id=int(author)).first().id for author in playlist_neighbors]
    author_json_list = list()
    for k in key:
        html = u"""
            <a class="avatar" href="/user_information/{}">
                <img src="/show_image/user_{}" class="round_icon" style="float:left"></a>
                <div id="info" class="info">
                <div class="title">
                    <a class="name" href="/user_information/{}">{}</a>
                </div>
                <ul>
                    <li class="li">
                        <div class="meta-block">
                            <a><p>{}</p>
                                <i class="iconfont ic-arrow">字数</i>
                            </a>
                        </div>
                    </li>
                    <li class="li">
                        <div class="meta-block">
                            <a><p>{}</p>
                                <i class="iconfont ic-arrow">喜欢</i>
                            </a>
                        </div>
                    </li>
                    <button data-v-test="" class="off {}" onclick="window.location.href='{}'

                    ">
                <i data-v-test="" class="iconfont">
                </i>
                <span style="color:{}">{}</span>
                </button>
                </ul>
            </div>
        </div>"""
        author = dict()
        author_instance = User.query.filter_by(id=k).first()
        author['name'] = author_instance.username
        author['id'] = k
        categories = Category.query.filter_by(user=k)
        word_count = sum(map(lambda x: len(x.content), categories.all()))
        author['word_count'] = word_count
        collect_num = categories.with_entities(func.sum(Category.collect_num)).first()[0] or 0
        author['collect_num'] = collect_num
        if not current_user.is_anonymous and author_instance.is_followed_by(current_user):
            url = "/unfollowed_user/{}".format(k)
            string = u"取消关注"
            color = "#8c8c8c"
            _class = "user-unfollow-button"
        else:
            url = "/followed_user/{}".format(k)
            string = u"关注"
            _class = "user-follow-button"
            color = "white"
        author_json_list.append(
            html.format(k, k, k, author['name'], author['word_count'], author['collect_num'], _class, url, color,
                        string))
    return json.dumps(author_json_list)


@dropdown.route('/autocomplete', methods=['GET', "POST"])
def autocomplete():
    info = request.args['term']
    doc_list = Category.query.whooshee_search(info, order_by_relevance=10).all()
    doc_list = list(map(lambda x: x.title, doc_list))
    return json.dumps(doc_list)
