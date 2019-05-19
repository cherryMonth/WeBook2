# coding=utf-8
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField, SubmitField, PasswordField, BooleanField, FileField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length
from app.main.models import Category


class PostForm(FlaskForm):
    title = StringField("", render_kw={'placeholder': u'主题(仅限于30字内...)'})
    location = StringField("", render_kw={'placeholder': u'地理位置(仅限于50字内...可选)'})
    text = TextAreaField("", [DataRequired(), Length(max=10000)])
    topic = StringField("", '文章主题', render_kw={'placeholder': u'为您的文章选个有趣的主题吧...'})
    topic_id = SelectMultipleField('Topic_id', coerce=int)
    submit = SubmitField(u"发布文章")

    def __init__(self, title="", text="", location="", topic=""):
        super(PostForm, self).__init__()
        if title:
            self.title.data = title
        if text:
            self.text.data = text
        if location:
            self.location.data = location
        if topic:
            self.topic.data = topic
        self.topic_id.choices = [(0, "国内主题"), (1,"国外主题"), (2, "特色主题")]

class FindFile(FlaskForm):
    input = StringField("", render_kw={'placeholder': u'输入您想查找的文章内容...'})
    submit = SubmitField(u"查找")


class FindUser(FlaskForm):
    input = StringField("", render_kw={'placeholder': u'输入您想查找的用户名...'})
    submit = SubmitField(u"查找")


class LoginForm(FlaskForm):
    email = StringField(u"邮箱")
    username = StringField(u'用户名')
    password = PasswordField(u'密码')
    remember_me = BooleanField(u'保持登录')
    submit = SubmitField(u'登录')


class CreateTopic(FlaskForm):
    topic_name = StringField(u'主题名称', validators=[DataRequired()], render_kw={'placeholder': u'输入您想创建的主题...'})
    filename = FileField(u"主题图片",  validators=[DataRequired()])
    topic_info = TextAreaField(u"主题简介",  validators=[DataRequired()])
    topic_id = SelectField('主题类型', coerce=int,  validators=[DataRequired()])
    submit = SubmitField(u'创建')

    def __init__(self, topic_name="", filename="", topic_info=""):
        super(CreateTopic, self).__init__()
        if topic_name:
            self.topic_name = topic_name
        if filename:
            self.topic_name = topic_name
        if topic_info:
            self.topic_info = topic_info
        self.topic_id.choices = [(0, "国内主题"), (1,"国外主题"), (2, "特色主题")]



class RegisterForm(FlaskForm):
    email = StringField(u'邮箱')
    username = StringField(u'用户名')
    filename = FileField(u"用户头像")
    about_me = TextAreaField(u"个人简介")
    password = PasswordField(u'密码')
    password2 = PasswordField(u'确认密码')
    submit = SubmitField(u'注册')

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)


class ForgetForm(FlaskForm):
    email = StringField(u'邮箱')
    submit = SubmitField(u'提交')


class EditInfoForm(FlaskForm):
    email = StringField(u'邮箱')
    submit = SubmitField(u'提交')


class EditBasic(FlaskForm):
    username = StringField(u'用户名')
    filename = FileField(u"上传用户头像")
    about_me = TextAreaField(u"个人简介")
    user_type = StringField(u'用户身份')
    submit = SubmitField(u'提交')


class EditPassword(FlaskForm):
    old = PasswordField(u"原密码")
    password = PasswordField(u'密码')
    password2 = PasswordField(u'确认密码')
    submit = SubmitField(u'提交')
