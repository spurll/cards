from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, PasswordField, HiddenField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import Required, NumberRange

from cards import app


class LoginForm(Form):
    username = TextField('Username', validators=[Required()])
    password = PasswordField('Password', validators=[Required()])
    remember = BooleanField('Remember Me', default=False)


class BrowseForm(Form):
    color = HiddenField(default='')
    type = HiddenField(default='')
    set = HiddenField(default='')
    collection = HiddenField(default='')


class DetailsForm(Form):
    pass


class AddForm(Form):
    name = TextField('Card Name', validators=[Required()])
    want = IntegerField('Want', default=app.config['DEFAULT_WANT'],
                        validators=[NumberRange(min=0)])

