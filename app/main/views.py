# coding=utf-8

from flask import redirect, flash, url_for, request, abort, send_from_directory, Response
from flask import Blueprint, current_app, session
from werkzeug.utils import secure_filename
from app.main.forms import PostForm, FindFile, EditInfoForm, EditBasic, EditPassword, CreateTopic
from flask_login import login_required, current_user
from app import db
from app.main.models import Category, Favorite, User, Comment, Topic, Information
import datetime
from ..email import send_email
import os
from flask import render_template, g
import time
from sqlalchemy import text
from sqlalchemy.sql import func
import subprocess
from app.main.auth import logout
import cgi
# from tornado.ioloop import IOLoop
import re
import base64

main = Blueprint("main", __name__)

file_dir = os.getcwd() + "/markdown"

user_page = dict()


def pop(args):
    print(str(args[0]) + "has pop!")
    user_page.pop(args[0], None)


def work(_id, info):
    print(_id + "begin work")
    name = _id + ".md"
    pdf = _id + ".pdf"
    filename = file_dir + "/" + name
    print(filename)
    pdf_name = file_dir + "/" + pdf
    _file = open(filename, "wb")
    line_list = info.split("\n")
    pattren = re.compile(r"\|.+\|")
    begin = re.compile(r"\|[-]+\|")

    tmp = ""
    status = False

    for line in line_list:
        if begin.match("".join(line.split())) and tmp:
            status = True
        elif pattren.match(line.strip()) and not status:
            if tmp:
                _file.write(tmp + "\n")
            tmp = line
            continue
        elif status and not pattren.match(line.strip()):
            status = False
        if status:
            if tmp:
                _file.write(cgi.escape(tmp) + "\n")
            _file.write(cgi.escape(line) + "\n")
        else:
            if tmp:
                _file.write(tmp + "\n")
            _file.write(line + "\n")
        tmp = ""

    if tmp:
        _file.write(tmp + "\n")
    _file.close()
    user_page[_id] = 'work'
    # IOLoop.instance().add_timeout(50, callback=pop, args=(_id,))
    os.system("pandoc {} --template eisvogel  --pdf-engine xelatex   -o {} -V CJKmainfont='SimSun'  "
              "--highlight-style pygments --listings ".format(filename, pdf_name))


@main.route("/create_doc", methods=['GET', "POST"])
@login_required
def edit():
    form = PostForm()
    p = Category()
    domestic_list = Topic.query.filter_by(type_id=0).all()
    foreign_list = Topic.query.filter_by(type_id=1).all()
    unique_list = Topic.query.filter_by(type_id=2).all()
    if request.method == "POST":

        p.title = form.title.data
        p.content = form.text.data
        p.user = current_user.id
        p.location = form.location.data
        p.topic = form.topic.data
        p.update_time = datetime.datetime.utcnow()
        db.session.add(p)
        db.session.commit()
        for _user in current_user.followers:
            info = Information()
            info.launch_id = current_user.id
            info.receive_id = _user.follower_id
            info.time = datetime.datetime.utcnow()
            db.session.add(info)
            db.session.flush()
            info.info = u"您关注的用户 " + current_user.username + u" 发表了新的文章 " + u"<a style='color: #d82433' " \
                                                                            u"href='{}?check={}'>{}</a>".format(
                u"/display/" + str(p.id), info.id, p.title) + u"。"
        # t = threading.Thread(target=work, args=(str(p.id), p.content.encode("utf-8")))
        # t.start()
        db.session.commit()

        flash(u'保存成功！', 'success')
        return redirect(url_for('main.edit'))
    return render_template('edit.html', form=form, domestic_list=domestic_list, foreign_list=foreign_list,
                           unique_list=unique_list)


@main.route("/", methods=['GET', "POST"])
def index():
    return render_template("index.html")


@main.route("/user_information/<int:key>", methods=['GET', "POST"])
def user_information(key):
    user = User.query.filter_by(id=key).first_or_404()
    follow = len(user.followed.all())  # 关注人数
    fans = len(user.followers.all())  # 粉丝人数
    category = len(user.categories.all())
    categories = Category.query.filter_by(user=key)
    word_count = sum(map(lambda x: len(x.content), categories.all()))
    collect_num = categories.with_entities(func.sum(Category.collect_num)).first()[0] or 0
    return render_template("user_info.html", user=user, follow=follow, fans=fans, category=category,
                           word_count=word_count, collect_num=collect_num)


@main.route("/display/<key>", methods=['GET', "POST"])
def dispaly(key):
    map_key = os.environ.get('map_key')
    p = Category.query.filter_by(id=key).first()
    if not current_user.is_anonymous:
        is_collect = Favorite.query.filter_by(favorited_id=key, favorite_id=current_user.id).first()
        if 'check' in request.args:
            temp = Information.query.filter_by(id=int(request.args['check'])).first()
            temp.confirm = True
            db.session.add(temp)
            db.session.commit()
            message_nums = len([info for info in current_user.received if info.confirm is False])
            if message_nums > 0:
                g.message_nums = message_nums
            else:
                g.message_nums = None
    else:
        is_collect = None
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)

    star_list = [p.five_num, p.four_num, p.three_num, p.two_num, p.one_num]
    people_num = sum(star_list)
    if people_num == 0:
        rate_list = [0, 0, 0, 0, 0]
    else:
        rate_list = list(map(lambda x: 1.0 * x / people_num * 100, star_list))

    comments = Comment.query.filter_by(post_id=key).all()
    for _index in range(len(comments)):
        comments[_index].author = User.query.filter_by(id=comments[_index].author_id).first().username
        comments[_index].img = comments[_index].author_id

        if comments[_index].comment_user_id or 0 > 0:
            comments[_index].comment_user = User.query.filter_by(id=comments[_index].comment_user_id).first().username

    return render_template("display.html", post=p, is_collect=is_collect, comments=comments, rate=p.rate,
                           people_num=people_num, rate_list=rate_list, location=p.location, map_key=map_key)


@main.route("/cancel/<key>", methods=['GET', "POST"])
@login_required
def cancel(key):
    p = Category.query.filter_by(id=key).first()
    user = User.query.filter_by(id=p.user).first()
    if not current_user.is_anonymous:
        is_collect = Favorite.query.filter_by(favorited_id=key, favorite_id=current_user.id).first()
    else:
        is_collect = None
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)
    if not is_collect:
        flash(u"您没有收藏该文章,无法取消收藏!", "warning")
        return redirect("/display/" + key)
    else:
        db.session.delete(is_collect)
        p.collect_num -= 1
        user.collect_num -= 1
        db.session.add(p)
        db.session.add(user)
        db.session.commit()
        flash(u"取消收藏成功!", "success")
        return redirect("/display/" + key)


@main.route("/show_collect/<int:key>", methods=['GET', "POST"])
def show_collect(key=0):
    if key == 0:
        collects = Favorite.query.filter_by(favorite_id=current_user.id).all()
    else:
        collects = Favorite.query.filter_by(favorite_id=key).all()

    doc_list = list()

    for _collect in collects:
        page = Category.query.filter_by(id=_collect.favorited_id).first()
        page.update_time = Favorite.query.filter_by(favorited_id=_collect.favorited_id).first().update_time
        doc_list.append(page)

    return render_template("collect.html", doc_list=doc_list, length=len(doc_list))


@main.route("/del_file/<int:key>/<int:page>", methods=['GET', "POST"])
@login_required
def del_file(key, page):
    p = Category.query.filter_by(id=key, user=current_user.id).first()
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)
    current_user.collect_num -= p.collect_num
    db.session.add(current_user)
    filename = os.getcwd() + "/markdown/" + str(p.id) + ".pdf"
    if os.path.exists(filename):
        os.system("rm -f {} ".format(filename))
    db.session.delete(p)
    db.session.commit()
    flash(u'删除成功！', 'success')
    return redirect(url_for("main.my_doc", key=current_user.id, _id=page))


"""
pandoc -s --smart --latex-engine=xelatex -V CJKmainfont='SimSun' -V mainfont="SimSun" -V geometry:margin=1in test.md  -o output.pdf
"""


@main.route("/collect/<key>", methods=['GET', 'POST'])
@login_required
def collect(key):
    p = Category.query.filter_by(id=key).first()
    user = User.query.filter_by(id=p.user).first()
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)
    f = Favorite()
    f.favorite_id = current_user.id
    f.update_time = datetime.datetime.utcnow()
    f.favorited_id = key
    p.collect_num += 1
    user.collect_num += 1
    f.update_time = datetime.datetime.utcnow()
    if Favorite.query.filter_by(favorite_id=current_user.id, favorited_id=key).first():
        flash(u'文章已经收藏！', 'warning')
        return redirect("/display/" + key)

    db.session.add(f)
    db.session.add(p)
    db.session.add(user)
    db.session.commit()
    flash(u'收藏成功！', 'success')
    return redirect("/display/" + key)


@main.route("/edit_file/<int:key>", methods=['GET', "POST"])
@login_required
def edit_file(key):
    p = Category.query.filter_by(id=key, user=current_user.id).first()
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)
    domestic_list = Topic.query.filter_by(type_id=0).all()
    foreign_list = Topic.query.filter_by(type_id=1).all()
    unique_list = Topic.query.filter_by(type_id=2).all()
    form = PostForm(title=p.title, text=p.content, location=p.location, topic=p.topic)
    if request.method == "POST":
        p.topic = request.values.get('topic')
        p.location = request.values.get('location')
        p.title = request.values.get("title")
        p.content = request.values.get("text")
        p.update_time = datetime.datetime.utcnow()
        filename = os.getcwd() + "/markdown/" + str(p.id) + ".pdf"
        if os.path.exists(filename):
            os.system("rm -f {} ".format(filename))
        db.session.add(p)
        db.session.commit()
        # t = threading.Thread(target=work, args=(str(p.id), p.content.encode("utf-8")))
        # t.start()
        flash(u'保存成功！', 'success')
        return redirect(url_for('main.edit'))
    return render_template('edit.html', form=form, domestic_list=domestic_list, foreign_list=foreign_list,
                           unique_list=unique_list)


@main.route("/download/<key>", methods=['GET'])
@login_required
def downloader(key):
    p = Category.query.filter_by(id=key, user=current_user.id).first()
    if not p:
        flash(u'该文章不存在！', 'warning')
        abort(404)

    pdf = str(p.id) + ".pdf"
    pdf_name = file_dir + "/" + pdf

    if os.path.exists(pdf_name):
        return send_from_directory(file_dir, pdf, as_attachment=True)

    popen = None
    if not user_page.has_key(str(p.id)):
        user_page[str(p.id)] = 'work'
        print(str(p.id) + "begin work")
        info = p.content.encode("utf-8")
        name = str(p.id) + ".md"
        pdf = str(p.id) + ".pdf"
        filename = file_dir + "/" + name
        pdf_name = file_dir + "/" + pdf
        _file = open(filename, "wb")
        line_list = info.split("\n")
        pattren = re.compile(r"\|.+\|")
        begin = re.compile(r"\|[-]+\|")

        tmp = ""
        status = False

        for line in line_list:
            if begin.match("".join(line.split())) and tmp:
                status = True
            elif pattren.match(line.strip()) and not status:
                if tmp:
                    _file.write(tmp + "\n")
                tmp = line
                continue
            elif status and not pattren.match(line.strip()):
                status = False
            if status:
                if tmp:
                    _file.write(cgi.escape(tmp) + "\n")
                _file.write(cgi.escape(line) + "\n")
            else:
                if tmp:
                    _file.write(tmp + "\n")
                _file.write(line + "\n")
            tmp = ""

        if tmp:
            _file.write(tmp + "\n")
        _file.close()

        user_page[str(p.id)] = 'work'

        shell = "pandoc {} --template eisvogel  --pdf-engine xelatex   -o {} -V CJKmainfont='SimSun'  " \
                "--highlight-style pygments --listings ".format(filename, pdf_name)
        import shlex
        popen = subprocess.Popen(shlex.split(shell), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # IOLoop.instance().add_timeout(50, callback=pop, args=(str(p.id),))
    else:
        print("have one working")
    count = 0

    while True:
        if os.path.exists(pdf_name):
            return send_from_directory(file_dir, pdf, as_attachment=True)

        elif count == 50:
            flash(u'导出失败, 请检查您的文档!(例如:图片格式只能使用jpg,png, Latex语法只支持XeLax!)', 'warning')
            # IOLoop.instance().add_timeout(0, callback=pop, args=(str(p.id),))
            return redirect(url_for("main.my_doc", key=current_user.id, _id=1))
        else:
            if popen and popen.poll() is None:
                line = popen.stdout.readline()
                line += popen.stderr.readline()
                print(line)
                if 'Error' in line or 'Warning' in line or "Could not" in line or 'WARNING' in line:
                    popen.terminate()
                    flash(u'导出失败, {}'.format(line), 'warning')
                    # IOLoop.instance().add_timeout(0, callback=pop, args=(str(p.id),))
                    return redirect(url_for("main.my_doc", key=current_user.id, _id=1))
            count += 1
            time.sleep(1)


@main.route("/find_file/<int:key>", methods=['GET', 'POST'])  # 七天最高
def find_file(key):
    form = FindFile()
    if key == 7:
        hot_doc_list = Category.query.from_statement(text("SELECT * FROM webook.category where DATE_SUB(CURDATE(), "
                                                          "INTERVAL 7 DAY) <= date(update_time) ORDER BY collect_num desc,update_time desc  LIMIT 10 ;")).all()
    else:
        hot_doc_list = Category.query.from_statement(text("SELECT * FROM webook.category ORDER BY "
                                                          "collect_num desc,update_time desc LIMIT 10 ;")).all()
    for doc in hot_doc_list:
        doc.username = User.query.filter_by(id=doc.user).first().username
    if form.validate_on_submit():
        doc_list = Category.query.whooshee_search(form.input.data).all()

        for doc in doc_list:
            doc.username = User.query.filter_by(id=doc.user).first().username
        length = len(doc_list)
        if not doc_list:
            flash(u"没有找到符合要求的文章!", "warning")
            return redirect(url_for("main.find_file", key=7))

        return render_template("find_file.html", form=form, doc_list=doc_list, length=length, key=7)
    return render_template("find_file.html", form=form, hot_doc_list=hot_doc_list, key=key)


@main.route("/edit_email", methods=['GET', 'POST'])
@login_required
def edit_email():
    form = EditInfoForm()

    if request.method == "POST":

        # filter 支持表达式 比 filter 更强大

        if User.query.filter_by(email=form.email.data).first() and current_user.email != form.email.data:
            flash(u"该邮箱已经被注册过，请重新输入!", "warning")
            return redirect(url_for("main.edit_info"))

        current_user.email = form.email.data
        current_user.confirmed = False
        db.session.add(current_user)
        db.session.commit()

        token = current_user.generate_confirmation_token()
        send_email([current_user.email], u'验证您的账号',
                   'auth/email/confirm', user=current_user, token=token)

        flash(u"一封验证邮件发送到了你的邮箱,请您验收!", "success")

        logout()
        return redirect(url_for("auth.login"))

    return render_template("edit/edit_email.html", form=form)


@main.route("/create_topic", methods=['GET', 'POST'])
@login_required
def create_topic():
    form = CreateTopic()
    if request.method == "POST":
        # filter 支持表达式 比 filter 更强大
        topic = Topic.query.filter_by(topic_name=form.topic_name.data, type_id=form.topic_id.data).first()
        if topic:
            flash(u"该主题已经被创建过，请重新输入!", "warning")
            return redirect(url_for("main.create_topic"))
        else:
            topic = Topic()
        topic.topic_name = form.topic_name.data
        topic.topic_info = form.topic_info.data
        topic.type_id = form.topic_id.data
        topic.image_name = "null"
        _file = request.files['filename'] if 'filename' in request.files else None
        _type = _file.filename.split(".")[-1].lower()
        if _file:
            if not _type or _type not in ['jpeg', 'jpg', 'bmp', "png"]:
                flash(u"图片格式错误，当前只支持'jpeg', 'jpg', 'bmp', 'png'!", "warning")
                return redirect(url_for("main.create_topic"))

        topic.user_id = current_user.id
        topic.topic_info = form.topic_info.data
        info = Information()
        info.time = datetime.datetime.utcnow()
        info.launch_id = current_user.id
        info.receive_id = current_user.id
        db.session.add(info)
        db.session.flush()
        info.info = u"用户" + current_user.username + u"创建了专题 {}。".format(topic.topic_name)
        db.session.add(info)
        db.session.add(topic)
        db.session.commit()
        topic_id = Topic.query.filter_by(topic_name=form.topic_name.data, type_id=form.topic_id.data).first().id
        _file.save(os.path.join(current_app.config['PAGE_UPLOAD_FOLDER'], "topic_" + str(topic_id)))
        flash(u"创建成功", "success")
        return redirect(url_for("users.topic_manager", key=current_user.id))
    return render_template("edit/edit_topic.html", form=form)


@main.route("/edit_topic/<int:key>", methods=['GET', 'POST'])
@login_required
def edit_topic(key):
    form = CreateTopic()
    temp = Topic.query.filter_by(id=key).first_or_404()
    topic_id = temp.id
    topic_name = temp.topic_name
    topic_info = temp.topic_info
    topic_type_id = temp.type_id
    if request.method == "POST":
        # filter 支持表达式 比 filter 更强大
        topic = Topic.query.filter_by(topic_name=form.topic_name.data, type_id=form.topic_id.data).first()
        if topic and topic.user_id != current_user.id:
            flash(u"该主题已经被创建过，请重新输入!", "warning")
            return redirect(url_for("main.create_topic"))
        topic = Topic.query.filter_by(id=key).first_or_404()
        topic.topic_name = form.topic_name.data
        topic.topic_info = form.topic_info.data
        topic.type_id = form.topic_id.data

        _file = request.files['filename'] if 'filename' in request.files else None
        _type = _file.filename.split(".")[-1].lower()
        if _file:
            if not _type or _type not in ['jpeg', 'jpg', 'bmp', "png"]:
                flash(u"图片格式错误，当前只支持'jpeg', 'jpg', 'bmp', 'png'!", "warning")
                return redirect(url_for("main.edit_topic"))
        _file.save(os.path.join(current_app.config['PAGE_UPLOAD_FOLDER'], "topic_" + str(topic.id)))
        topic.topic_info = form.topic_info.data
        info = Information()
        info.time = datetime.datetime.utcnow()
        info.launch_id = current_user.id
        info.receive_id = current_user.id
        db.session.add(info)
        db.session.flush()
        info.info = u"用户" + current_user.username + u"修改了专题 {}。".format(topic.topic_name)
        db.session.add(info)
        db.session.add(topic)
        db.session.commit()
        flash(u"修改成功", "success")
        return redirect(url_for("main.edit_topic", key=topic.id))
    return render_template("edit/edit_topic.html", form=form, topic_id=topic_id, topic_name=topic_name,
                               topic_info=topic_info,
                               topic_type_id=topic_type_id)


@main.route("/edit_basic", methods=['GET', 'POST'])
@login_required
def edit_basic():
    form = EditBasic()
    form.user_type.data = ["Moderator", "Administrator", "User"][current_user.role_id - 1]
    if request.method == "POST":
        # filter 支持表达式 比 filter 更强大
        temp = User.query.filter_by(username=form.username.data).first()
        if temp is form.username.data and current_user.username != form.username.data:
            print(User.query.filter_by(username=form.username.data).first())
            print(current_user.username)
            print(form.username.data)
            print(current_user.username != form.username.data)
            print(current_user.username is form.username.data)
            flash(u"该用户名已经被注册过，请重新输入!", "warning")
            return redirect(url_for("main.edit_basic"))

        _file = request.files['filename'] if 'filename' in request.files else None
        if _file:
            _type = _file.filename.split(".")[-1].lower()
            if not _type or _type not in ['jpeg', 'jpg', 'bmp', "png"]:
                flash(u"图片格式错误，当前只支持'jpeg', 'jpg', 'bmp', 'png'!", "warning")
                return redirect(url_for("main.edit_basic"))
            _file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], "user_" + str(current_user.id)))
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()

        flash(u"修改成功!", "success")
        return redirect(url_for("main.index"))

    return render_template("edit/edit_basic.html", form=form)


@main.route("/edit_password", methods=['GET', 'POST'])
@login_required
def edit_password():
    form = EditPassword()

    if request.method == "POST":
        if session.get('check') != 'true' and not current_user.verify_password(form.old.data):
            flash(u"用户密码错误，请重新输入!", "warning")
            return redirect(url_for("main.edit_password"))

        current_user.password = form.password.data
        session['check'] = 'false'
        db.session.add(current_user)
        db.session.commit()

        flash(u"修改成功!", "success")
        return redirect(url_for("main.index"))

    return render_template("edit/edit_password.html", form=form)


@main.route("/add_comment/<key>", methods=["POST"])
@login_required
def add_comment(key):
    if request.method == "POST":
        info = request.form["comment"]
        if not Category.query.filter_by(id=key).first():
            abort(404)
        comment = Comment(body=cgi.escape(info), author_id=current_user.id, post_id=key)
        comment.timestamp = datetime.datetime.utcnow()
        _info = Information()
        _info.time = datetime.datetime.utcnow()
        _info.launch_id = current_user.id
        category = Category.query.filter_by(id=key).first()
        get_star = int(request.form['score']) if request.form.get('score') else 0
        print(get_star)
        if get_star != 0:
            if get_star == 1:
                category.one_num += 1
            elif get_star == 2:
                category.two_num += 1
            elif get_star == 3:
                category.three_num += 1
            elif get_star == 4:
                category.four_num += 1
            elif get_star == 5:
                category.five_num += 1
            num = sum([category.five_num, category.four_num, category.three_num, category.two_num, category.one_num])
            if num > 0:
                category.rate = 5.0 * category.five_num / num + 4.0 * category.four_num / num + 3.0 * category.three_num / num + 2.0 * category.two_num / num + 1.0 * category.one_num / num
            db.session.add(category)
        comment.comment_rate = get_star
        _info.receive_id = category.user
        db.session.add(_info)
        db.session.flush()
        _info.info = u"用户" + current_user.username + u" 对您的文章" + u"<a style='color: #d82433' " \
                                                                 u"href='{}?check={}'>{}</a>".format(
            u"/display/" + str(category.id), _info.id, category.title) + u"进行了评论!"
        db.session.add(_info)
        db.session.add(comment)
        db.session.commit()
        flash(u"添加成功!", "success")
        return redirect("/display/" + key)


@main.route("/edit_comment/<key>", methods=["POST"])
@login_required
def edit_comment(key):
    if request.method == "POST":
        info = request.form["comment"]
        comment = Comment.query.filter_by(id=key).first()
        if not comment:
            abort(404)
        comment.body = info
        _info = Information()
        _info.time = datetime.datetime.utcnow()
        _info.launch_id = current_user.id
        category = Category.query.filter_by(id=comment.post_id).first()
        _info.receive_id = category.user
        db.session.add(_info)
        db.session.flush()
        _info.info = u"用户" + current_user.username + u" 对您的文章" + u"<a style='color: #d82433' " \
                                                                 u"href='{}?check={}'>{}</a>".format(
            u"/display/" + str(category.id), _info.id, category.title) + u"修改了评论!"
        db.session.add(_info)
        comment.timestamp = datetime.datetime.utcnow()
        db.session.add(comment)
        db.session.commit()
        flash(u"修改成功!", "success")
        return redirect("/display/" + str(comment.post_id))


@main.route("/response_comment/<int:post_id>/<int:key>", methods=["POST"])
@login_required
def response_comment(post_id, key):
    if request.method == "POST":
        if request.method == "POST":
            info = request.form["comment"]
            if not Category.query.filter_by(id=post_id).first():
                abort(404)
            comment = Comment(body=cgi.escape(info), author_id=current_user.id, post_id=post_id)
            comment.comment_user_id = key
            _info = Information()
            _info.time = datetime.datetime.utcnow()
            _info.launch_id = current_user.id
            category = Category.query.filter_by(id=post_id).first()
            _info.receive_id = comment.comment_user_id
            comment.timestamp = datetime.datetime.utcnow()
            db.session.add(_info)
            db.session.add(comment)
            db.session.flush()
            _info.info = u"用户" + current_user.username + u" 对您在" + u"<a style='color: #d82433' " \
                                                                   u"href='{}?check={}'>{}</a>".format(
                u"/display/" + str(category.id), _info.id, category.title) + \
                         u"的评论进行了回复!"

            db.session.commit()
            flash(u"回复成功!", "success")
            return redirect("/display/" + str(post_id))


@main.route("/del_comment/<key>", methods=['GET', 'POST'])
@login_required
def del_comment(key):
    comment = Comment.query.filter_by(id=key).first()
    if not comment:
        abort(404)

    category = Category.query.filter_by(id=comment.post_id).first()  # 文章

    # 若是管理员，文章作者，评论作者都能删除评论

    if current_user.role.permissions >= 31 or current_user.id == comment.author_id or current_user.id == category.user:
        db.session.delete(comment)
        db.session.commit()
        flash(u"删除成功!", "success")
        return redirect("/display/" + str(category.id))

    else:
        flash(u"您无权删除该条评论!", "warning")
        return redirect("/display/" + str(category.id))


# @main.route("/disable_comment/<key>", methods=['POST'])
# @login_required
# def disable_comment(key):
#     comment = Comment.query.filter_by(id=key).first()
#     if not comment:
#         abort(404)
#
#     category = Category.query.filter_by(id=comment.post_id).first()  # 文章
#
#     # 管理员和作者可以屏蔽评论
#
#     if current_user.role >= 31 or current_user.id == category.user:
#         comment.disabled = True
#         db.session.add(comment)
#         db.session.commit()
#         flash(u"屏蔽成功!", "success")
#         return redirect(url_for("/display/" + category.id))
#     else:
#         flash(u"您无权屏蔽该条评论!", "warning")
#         return redirect(url_for("/display/" + category.id))


@main.route("/show_image/<key>", methods=['GET', 'POST'])
def show_image(key):
    if not os.path.exists(current_app.config['PAGE_UPLOAD_FOLDER'] + key):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], "-1.jpg")
    else:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], key)


@main.route("/show_topic_image/<key>", methods=['GET', 'POST'])
def show_topic_image(key):
    if not os.path.exists(current_app.config['PAGE_UPLOAD_FOLDER'] + key):
        return send_from_directory(current_app.config['PAGE_UPLOAD_FOLDER'], "-1.jpg")
    else:
        return send_from_directory(current_app.config['PAGE_UPLOAD_FOLDER'], key)
