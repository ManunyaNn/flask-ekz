from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, DateField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date

class EventForm(FlaskForm):
    title = StringField('Название мероприятия', validators=[
        DataRequired(message='Название мероприятия обязательно'),
        Length(min=3, max=200, message='Название должно быть от 3 до 200 символов')
    ])
    description = TextAreaField('Описание мероприятия', validators=[
        DataRequired(message='Описание мероприятия обязательно'),
        Length(min=10, message='Описание должно содержать минимум 10 символов')
    ])
    date = DateField('Дата мероприятия', validators=[
        DataRequired(message='Дата мероприятия обязательна')
    ], format='%Y-%m-%d')
    location = StringField('Место проведения', validators=[
        DataRequired(message='Место проведения обязательно'),
        Length(min=3, max=200, message='Место проведения должно быть от 3 до 200 символов')
    ])
    required_volunteers = IntegerField('Требуемое количество волонтёров', validators=[
        DataRequired(message='Количество волонтёров обязательно'),
        NumberRange(min=1, max=1000, message='Количество волонтёров должно быть от 1 до 1000')
    ])
    image = FileField('Изображение мероприятия', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Разрешены только изображения: JPG, PNG, GIF')
    ])
    submit = SubmitField('Сохранить')

class EventEditForm(EventForm):
    """Форма редактирования (без поля изображения)"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image.validators = [Optional()]  # Делаем поле изображения необязательным при редактировании

class VolunteerRegistrationForm(FlaskForm):
    contact_info = StringField('Контактная информация', validators=[
        DataRequired(message='Контактная информация обязательна'),
        Length(min=5, max=200, message='Контактная информация должна быть от 5 до 200 символов')
    ])
    submit = SubmitField('Отправить заявку')