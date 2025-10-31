from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[
        DataRequired(message='Поле логин обязательно для заполнения'),
        Length(min=3, max=80, message='Логин должен быть от 3 до 80 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Поле пароль обязательно для заполнения')
    ])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')