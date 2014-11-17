from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, PasswordField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import Required, NumberRange


class LoginForm(Form):
    username = TextField("Username", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    remember = BooleanField("Remember Me", default=False)


class AddForm(Form):
    name = TextField(label="Card Name", validators=[Required()])
    set = TextField(label="Set", validators=[Required()])
    have = IntegerField(label="Have", default=0,
                        validators=[NumberRange(min=0)])

