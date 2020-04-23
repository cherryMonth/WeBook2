# coding=utf-8

from flask import render_template, redirect, flash, url_for, request, abort, Response
from flask import Blueprint, current_app, send_from_directory
import os
import re
from app.main.parse import Extractor
import markdown
from app.main.models import Category, Comment, Topic
from app.main.forms import FindUser
from app.main.models import User, Information
from app import db
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from sqlalchemy import text
import json

user = Blueprint("users", __name__)


@user.route("/find_user", methods=['POST', 'GET'])
def find_user():
    form = FindUser()

    hot_user_list = User.query.from_statement(
        text("SELECT * FROM users ORDER BY collect_num DESC LIMIT 5 ;")).all()

    if form.validate_on_submit():
        user_list = User.query.whooshee_search(form.input.data).all()

        length = len(user_list)
        if not user_list:
            flash(u"没有找到符合要求的用户!", "warning")
            return redirect(url_for("users.find_user"))

        return render_template("find_user.html", form=form, user_list=user_list, length=length)
    return render_template("find_user.html", form=form, hot_user_list=hot_user_list)


@user.route("/followed_user/<key>", methods=['GET', 'POST'])
@login_required
def followed_user(key):
    _user = User.query.filter_by(id=key).first()
    if not _user:
        flash(u"用户不存在!", "warning")
    elif current_user.is_following(_user):
        flash(u"您已经关注了此用户，无法重复关注!", "warning")
    else:
        current_user.follow(_user)
        _info = Information()
        _info.launch_id = current_user.id
        _info.receive_id = _user.id
        _info.info = u"用户" + current_user.username + u" 对用户 {} 进行了关注!".format(_user.username)
        db.session.add(_info)
        flash(u"关注成功!", "success")
    return redirect(request.referrer)


@user.route("/unfollowed_user/<key>", methods=['GET', 'POST'])
@login_required
def unfollowed_user(key):
    _user = User.query.filter_by(id=key).first()
    if not _user:
        flash(u"用户不存在!", "warning")
    elif not current_user.is_following(_user):
        flash(u"您尚未关注此用户，无法取消关注!", "warning")
    else:
        _info = Information()
        _info.launch_id = current_user.id
        _info.receive_id = _user.id
        _info.info = u"用户" + current_user.username + u" 对您取消了关注!"
        db.session.add(_info)
        current_user.unfollow(_user)
        flash(u"取消关注成功!", "success")
    return redirect(request.referrer)


@user.route("/information/<int:page>", methods=['GET', 'POST'])
@login_required
def information(page):
    temp = Information.query.filter_by(receive_id=current_user.id)
    info_list = temp.order_by(Information.time.desc()).paginate(page, 10, error_out=True).items
    length = len(temp.all())
    page_num = int(length / 10 if length % 10 == 0 else length / 10 + 1)
    for index in range(len(info_list)):
        info_list[index].author = User.query.filter_by(id=info_list[index].launch_id).first()
    return render_template("information.html", info_list=info_list, length=length, page=page, page_num=page_num)


@user.route("/info_confirm/<int:key>/<int:page>", methods=['GET', 'POST'])
@login_required
def confirm(key, page):
    info = Information.query.filter_by(id=key).first()
    if not info:
        flash(u"信息不存在!", "warning")
    elif info.confirm is True:
        flash(u"信息已被忽略，无法再次忽略!", "warning")
    elif info.receive_id != current_user.id:
        flash(u"您不是此信息的接收者，无法忽略此消息!", "warning")
    else:
        info.confirm = True
        flash(u"信息确认成功!", "success")
        db.session.add(info)
        db.session.commit()
    return redirect(url_for("users.information", page=page))


@user.route("/del_info/<int:key>/<int:page>", methods=['GET', 'POST'])
@login_required
def del_info(key, page):
    info = Information.query.filter_by(id=key).first()
    if not info:
        flash(u"信息不存在!", "warning")
    elif info.receive_id != current_user.id:
        flash(u"您不是此信息的接收者，无法删除!", "warning")
    else:
        info.confirm = True
        flash(u"信息删除成功!", "success")
        db.session.delete(info)
        db.session.commit()
    return redirect(url_for("users.information", page=page))


@user.route("/get_user_info/", methods=['GET', 'POST'])
def get_user_info():
    key = request.args.get('email') or ""
    password = request.args.get('password')
    _user = User.query.filter_by(email=key).first()
    info = dict()
    if password and _user and _user.verify_password(password):
        # 对象的序列化为字典 info.update(_user.__dict__)
        info['username'] = _user.username
        info['follow_num'] = _user.follow_num
        info['image_name'] = "https://www.webook.mobi/show_image/user_{}".format(_user.id)
        info['about_me'] = _user.about_me
        info['id'] = _user.id
        info['collect_num'] = _user.collect_num
        info['email'] = _user.email
    return json.dumps(info)


@user.route("/send_info/<int:key>", methods=["POST"])
@login_required
def send_info(key):
    info = Information()
    _user = User.query.filter_by(id=key).first()

    if not _user:
        abort(404)

    info.launch_id = current_user.id
    info.receive_id = _user.id
    info.is_privacy = True
    info.info = request.form.get('text')
    db.session.add(info)
    db.session.commit()
    flash(u"发送成功!", "success")
    return redirect(request.referrer)


@user.route("/upload_images", methods=['POST', "GET"])
@login_required
def upload_images():
    _file = request.files.get('editormd-image-file')
    result = dict()
    filename = _file.filename
    if os.path.exists(current_app.config['PAGE_UPLOAD_FOLDER'] + filename):
        result['success'] = 0
        result['message'] = u"该文件名已经存在，无法覆盖!"
        result['url'] = None
        return json.dumps(result)
    _type = filename.split(".")[-1].lower()
    if not _type or _type not in ["jpg", "jpeg", "gif", "png", "bmp", "webp"]:
        result['success'] = 0
        result['message'] = u"图片格式错误，当前只支持'jpeg', 'jpg', 'bmp', 'png', 'webp'" \
                            u", 'gif'!"
        result['url'] = None
        return json.dumps(result)
    else:
        _file.save(os.path.join(current_app.config['PAGE_UPLOAD_FOLDER'], filename))
        result['success'] = 1
        result['message'] = u"上传成功!"
        if eval(os.environ['produce']):
            result['url'] = "https://www.webook.mobi/display_images/{}".format(filename)
        else:
            result['url'] = request.url_root + "display_images/{}".format(filename)
        return json.dumps(result)


@user.route("/display_images/<filename>", methods=['GET'])
def display_images(filename):
    if not os.path.exists(current_app.config['PAGE_UPLOAD_FOLDER'] + filename):
        return send_from_directory(current_app.config['PAGE_UPLOAD_FOLDER'], "-1.jpg")
    else:
        return send_from_directory(current_app.config['PAGE_UPLOAD_FOLDER'], filename)


@user.route('/get_category', methods=['GET', "POST"])
def get_category():
    key = int(request.args['key'])
    _id = int(request.args['_id'])
    temp = Category.query.filter_by(user=key)
    length = len(temp.all())
    target_page_num = 5
    page_num = int(length / target_page_num if length % target_page_num == 0 else length / target_page_num + 1)
    if _id > page_num:
        return '[]'
    docs = temp.order_by(Category.id.desc()).paginate(_id, target_page_num, error_out=True).items
    docs_html_list = list()
    for doc in docs:
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
        image_url = result[0][:-1] if result else "https://www.webook.mobi/display_images/purple-4163951_1280.jpg"

        exts = ['markdown.extensions.extra', 'markdown.extensions.codehilite', 'markdown.extensions.tables',
                'markdown.extensions.toc']
        ext = Extractor(0)
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


@user.route('/get_topic_category', methods=['GET', "POST"])
def get_topic_category():
    key = int(request.args['key']) if request.args.get('key') else 0
    num = int(request.args['num'])
    topic_id = int(request.args['topic_id'])
    if key == 0:
        temp = Category.query.filter_by(topic=topic_id)
    else:
        temp = Category.query.filter_by(user=key, topic=topic_id)
    length = len(temp.all())
    target_page_num = 5
    page_num = int(length / target_page_num if length % target_page_num == 0 else length / target_page_num + 1)
    if num > page_num:
        return '[]'
    docs = temp.order_by(Category.id.desc()).paginate(num, target_page_num, error_out=True).items
    docs_html_list = list()
    for doc in docs:
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
        image_url = result[0][:-1] if result else "https://www.webook.mobi/display_images/purple-4163951_1280.jpg"

        exts = ['markdown.extensions.extra', 'markdown.extensions.codehilite', 'markdown.extensions.tables',
                'markdown.extensions.toc']
        ext = Extractor(0)
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


@user.route('/get_dynamics', methods=['GET', "POST"])
def get_dynamics():
    key = int(request.args['key'])
    _id = int(request.args['_id'])
    tmp = Information.query.filter_by(launch_id=key, is_privacy=False).order_by(Information.time.desc())
    length = len(tmp.all())
    target_page_num = 5
    page_num = int(length / target_page_num if length % target_page_num == 0 else length / target_page_num + 1)
    if _id > page_num:
        return '[]'
    info_list = tmp.paginate(_id, target_page_num, error_out=True).items
    info_html_list = list()
    for info in info_list:
        html = u"""<li id="{}" class="have-img" style="margin-left: 22%">
                        <a class="avator" href="/user_information/{}">
                        <img class="round_icon" src={} style="float:left;">
                        </a>
                        <div class="title">
                        <a class="name">{}</a>
                        </div>
                        <div style="margin-top: 10px;">
                            <p  class="abstract" style="margin-left: 80px;">
                                {}
                            </p>
                            </div>
                            <div class="meta">
                                <span style="margin-left: 20px" class="flask-moment" data-timestamp="{}" data-format="fromNow(0)" data-refresh="0">{}</span>
                            </div>
                        </div>
                    </li>"""

        image_url = "/show_image/user_{}".format(info.launch_id)
        lauch_name = User.query.filter_by(id=info.launch_id).first_or_404().username
        update_time = str(info.time)
        html = html.format(info.id, info.launch_id, image_url, lauch_name, info.info, update_time, update_time)
        item = dict()
        item['html'] = html
        item['id'] = info.id
        info_html_list.append(item)
    return json.dumps(info_html_list)


@user.route("/my_follow", methods=['GET', 'POST'])
@login_required
def my_follow():
    users = current_user.followed
    user_list = [User.query.filter_by(id=_user.followed_id).first() for _user in users]
    return render_template("edit/edit_my_follow.html", user_list=user_list)


@user.route("/follow_my", methods=['GET', 'POST'])
@login_required
def follow_me():
    users = current_user.followers
    user_list = [User.query.filter_by(id=_user.follower_id).first() for _user in users]
    return render_template("edit/edit_follow_me.html", user_list=user_list)


@user.route("/get_comment", methods=['GET', 'POST'])
def get_comment():
    key = int(request.args['key'])
    _id = int(request.args['_id'])
    target_page_num = 5
    recent_doc_list = Category.query.from_statement(text("""select category.id, category.content, category.title, update_time, timestamp,  category.collect_num , category.rate
from category, comment where category.id = comment.post_id and category.user = {} order by timestamp desc;""".format(
        key))).all()
    cache = []
    for t in recent_doc_list:
        if t.id not in cache:
            cache.append(t.id)
        else:
            recent_doc_list.remove(t)
    if target_page_num * _id - target_page_num > len(recent_doc_list) - 1:
        return '[]'

    recent_doc_list = recent_doc_list[target_page_num * _id - target_page_num:target_page_num]
    docs_html_list = list()
    for doc in recent_doc_list:
        html = u"""<li id="{}" class="have-img">
                            <a class="warp-img" href="/display/{}">
                            <img class="  img-blur-done" src={} style="float:right;margin-right:37%" height=100 width=125>
                            </a>
                            <div style="margin-top: 20px;" class="container">
                                <a class="title" target="_blank" href="/display/{}">{}</a>
                                <p  class="abstract" style="cursor:pointer" onclick="window.location='/display/{}#post-tabs';">
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
        image_url = result[0][:-1] if result else "https://www.webook.mobi/display_images/purple-4163951_1280.jpg"

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


@user.route("/get_hot", methods=['GET', 'POST'])
def get_hot():
    key = int(request.args['key'])
    _id = int(request.args['_id'])
    tmp = Category.query.filter_by(user=key).order_by(Category.rate.desc()). \
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
        image_url = result[0][:-1] if result else "https://www.webook.mobi/display_images/purple-4163951_1280.jpg"

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


@user.route("/topic_manager/<int:key>", methods=['GET', 'POST'])
def topic_manager(key):
    if key == 0:
        domestic_list = Topic.query.filter_by(type_id=0).all()
        foreign_list = Topic.query.filter_by(type_id=1).all()
        unique_list = Topic.query.filter_by(type_id=2).all()
    else:
        domestic_list = Topic.query.filter_by(type_id=0, user_id=key).all()
        foreign_list = Topic.query.filter_by(type_id=1, user_id=key).all()
        unique_list = Topic.query.filter_by(type_id=2, user_id=key).all()
    first_topic = None
    if domestic_list:
        first_topic = domestic_list[0]
    elif foreign_list:
        first_topic = foreign_list[0]
    elif unique_list:
        first_topic = unique_list[0]
    return render_template("topic_manager.html", domestic_list=domestic_list, foreign_list=foreign_list,
                           unique_list=unique_list, first_topic=first_topic, key=key)


@user.route('/get_topic_info', methods=['GET', 'POST'])
def get_topic_info():
    key = int(request.args.get('key'))
    topic = Topic.query.filter_by(id=key).first_or_404()
    user = User.query.filter_by(id=topic.user_id).first_or_404()
    if current_user.is_authenticated and topic.user_id == current_user.id:
        edit_topic_html = u"""<div style="float:right;">
                            <a href="/edit_topic/{}">修改主题信息</a>
                         </div>""".format(topic.id)
    else:
        edit_topic_html = ""
    html = u"""<div style="float:left;">
                    <a id="topic_info" class="warp-img">
                        <img id='topic_image' style="margin-left: 20px;"
                             src='/show_topic_image/topic_{}'
                             style="float:right;margin-right:37%" height="200" width="250">
                    </a>
                </div>
                {}
                <div>
                    <div class="li_title" style="float: left" id="topic_title">
                       {}
                    </div>
                    <br>
                    <div>
                        <p class="abstract" id="topic_text">{}</p>
                    </div>
                    <div id="user_info" style="margin-top: 100px;margin-left: 80%" class="container">
                        <a class="avatar" href="/user_information/{}">
                            <img src="/show_image/user_{}" class="round_icon" style="float:left"></a>
                        <div id="info" class="info">
                        <div class="title">
                            <a class="name" href="/user_information/{}">{}</a>
                        </div>
                        <span style="margin-left: 20px" class="flask-moment" data-timestamp="{}" data-format="fromNow(0)" data-refresh="0">{}</span>
                    </div>
                """
    return html.format(topic.id, edit_topic_html, topic.topic_name, topic.topic_info, user.id, user.id, user.id,
                       user.username,
                       topic.create_time, topic.create_time)
