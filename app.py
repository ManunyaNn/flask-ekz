from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from datetime import date
from forms import LoginForm
from models import db, User, Event, Role, VolunteerRegistration
from flask import render_template, request, redirect, url_for, flash, current_app
from forms import EventForm, EventEditForm
from utils import save_image, sanitize_html
from forms import VolunteerRegistrationForm
import markdown
import os

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# Конфигурация
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Замените на случайный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Главная страница со списком мероприятий
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Получаем только будущие мероприятия, отсортированные по дате (сначала новые)
    events_query = Event.query.filter(Event.date >= date.today()).order_by(Event.date.asc())
    
    # Пагинация
    events = events_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('index.html', events=events)

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже аутентифицирован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Ищем пользователя по логину
        user = User.query.filter_by(login=form.login.data).first()
        
        # Проверяем пользователя и пароль
        if user is None or not user.check_password(form.password.data):
            flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
            return render_template('login.html', form=form)
        
        # Выполняем вход
        login_user(user, remember=form.remember_me.data)
        
        # Перенаправляем на следующую страницу или на главную
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')
        
        flash(f'Добро пожаловать, {user.full_name}!', 'success')
        return redirect(next_page)
    
    return render_template('login.html', form=form)

# Выход из системы
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))



@app.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    # Проверка прав - только администратор
    if current_user.role.name != 'administrator':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    event_title = event.title
    
    try:
        # Удаляем мероприятие (каскадное удаление регистраций произойдет автоматически)
        db.session.delete(event)
        db.session.commit()
        flash(f'Мероприятие "{event_title}" успешно удалено', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при удалении мероприятия', 'danger')
        print(f"Error deleting event: {e}")
    
    return redirect(url_for('index'))





@app.route('/events/new', methods=['GET', 'POST'])
@login_required
def new_event():
    # Проверка прав - только администратор
    if current_user.role.name != 'administrator':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    form = EventForm()
    
    if form.validate_on_submit():
        try:
            # Сохраняем изображение
            image_filename = None
            if form.image.data:
                image_filename = save_image(form.image.data)
                if not image_filename:
                    flash('Ошибка при загрузке изображения', 'danger')
                    return render_template('event_new.html', form=form)
            
            # Создаем мероприятие
            event = Event(
                title=sanitize_html(form.title.data),
                description=form.description.data,  # Markdown сохраняем как есть
                date=form.date.data,
                location=sanitize_html(form.location.data),
                required_volunteers=form.required_volunteers.data,
                image_filename=image_filename or 'default_event.jpg',
                organizer_id=current_user.id
            )
            
            db.session.add(event)
            db.session.commit()
            
            flash('Мероприятие успешно создано!', 'success')
            return redirect(url_for('event_detail', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating event: {e}')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
    
    return render_template('event_new.html', form=form)

@app.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    form = EventEditForm(obj=event)
    
    if form.validate_on_submit():
        try:
            event.title = sanitize_html(form.title.data)
            event.description = form.description.data  # Markdown сохраняем как есть
            event.date = form.date.data
            event.location = sanitize_html(form.location.data)
            event.required_volunteers = form.required_volunteers.data
            
            db.session.commit()
            
            flash('Мероприятие успешно обновлено!', 'success')
            return redirect(url_for('event_detail', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating event: {e}')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
    
    return render_template('event_edit.html', form=form, event=event)

# Обновим маршрут просмотра мероприятия
@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Получаем регистрацию текущего пользователя (если есть)
    user_registration = None
    if current_user.is_authenticated:
        user_registration = event.get_user_registration(current_user.id)
    
    # Форма для регистрации
    form = VolunteerRegistrationForm()
    
    return render_template('event_detail.html', 
                         event=event, 
                         user_registration=user_registration,
                         form=form)

@app.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = VolunteerRegistrationForm()
    
    # Проверяем, что пользователь еще не зарегистрирован
    existing_registration = event.get_user_registration(current_user.id)
    if existing_registration:
        flash('Вы уже зарегистрированы на это мероприятие', 'warning')
        return redirect(url_for('event_detail', event_id=event.id))
    
    if form.validate_on_submit():
        try:
            # Создаем новую регистрацию
            registration = VolunteerRegistration(
                event_id=event.id,
                volunteer_id=current_user.id,
                contact_info=form.contact_info.data,
                status='pending'
            )
            
            db.session.add(registration)
            db.session.commit()
            
            flash('Ваша заявка успешно отправлена! Ожидайте подтверждения.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при отправке заявки', 'danger')
    
    return redirect(url_for('event_detail', event_id=event.id))

@app.route('/events/<int:event_id>/registration/<int:registration_id>/accept')
@login_required
def accept_registration(event_id, registration_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))
    
    event = Event.query.get_or_404(event_id)
    
    if event.accept_volunteer(registration_id):
        flash('Заявка волонтёра принята', 'success')
    else:
        flash('Не удалось принять заявку', 'danger')
    
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/events/<int:event_id>/registration/<int:registration_id>/reject')
@login_required
def reject_registration(event_id, registration_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))
    
    event = Event.query.get_or_404(event_id)
    
    if event.reject_volunteer(registration_id):
        flash('Заявка волонтёра отклонена', 'info')
    else:
        flash('Не удалось отклонить заявку', 'danger')
    
    return redirect(url_for('event_detail', event_id=event_id))

# Создание таблиц в базе данных
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)