from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date
import markdown

from app import db, login_manager



# Соединительная таблица для связи многие-ко-многим между мероприятиями и волонтерами
event_volunteers = db.Table('event_volunteers',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), primary_key=True),
    db.Column('volunteer_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    
    # Связь с пользователями
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    
    # Внешний ключ для роли
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    
    # Связи
    organized_events = db.relationship('Event', backref='organizer', lazy=True)
    volunteer_registrations = db.relationship('VolunteerRegistration', backref='volunteer', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.last_name} {self.first_name} {self.middle_name}"
        return f"{self.last_name} {self.first_name}"

class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    required_volunteers = db.Column(db.Integer, nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    
    # Внешний ключ для организатора
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Связи
    volunteers = db.relationship('User', secondary=event_volunteers, lazy='subquery',
        backref=db.backref('events_as_volunteer', lazy=True))
    registrations = db.relationship('VolunteerRegistration', backref='event', lazy=True, cascade='all, delete-orphan')

    @property
    def volunteers_count(self):
        """Количество ПРИНЯТЫХ волонтёров"""
        return VolunteerRegistration.query.filter_by(
            event_id=self.id, 
            status='accepted'
        ).count()
    
    @property
    def is_registration_open(self):
        #Открыта ли регистрация (не прошла дата и не набрано волонтёров)
        from datetime import date
        return self.date >= date.today() and self.volunteers_count < self.required_volunteers
    
    @property
    def registration_status(self):
        #Статус регистрации для отображения
        if self.date < date.today():
            return "Мероприятие прошло"
        elif self.volunteers_count >= self.required_volunteers:
            return "Регистрация закрыта"
        else:
            return "Идёт набор волонтёров"
    
    @property
    def description_html(self):
        """Конвертирует Markdown в безопасный HTML"""
        if self.description:
            # Сначала конвертируем Markdown в HTML
            html = markdown.markdown(self.description)
            # Затем санитайзим HTML
            return sanitize_html(html)
        return ""
    
    def get_accepted_volunteers(self):
        """Возвращает принятых волонтёров, отсортированных по дате регистрации (новые first)"""
        return VolunteerRegistration.query.filter_by(
            event_id=self.id, 
            status='accepted'
        ).order_by(VolunteerRegistration.registration_date.desc()).all()
    
    def get_pending_volunteers(self):
        """Возвращает волонтёров, ожидающих подтверждения"""
        return VolunteerRegistration.query.filter_by(
            event_id=self.id, 
            status='pending'
        ).order_by(VolunteerRegistration.registration_date.asc()).all()
    
    def get_user_registration(self, user_id):
        """Возвращает регистрацию конкретного пользователя"""
        return VolunteerRegistration.query.filter_by(
            event_id=self.id,
            volunteer_id=user_id
        ).first()
    
    def accept_volunteer(self, registration_id):
        """Принимает волонтёра и обрабатывает автоматическое отклонение остальных при наборе лимита"""
        registration = VolunteerRegistration.query.get(registration_id)
        if registration and registration.status == 'pending':
            registration.status = 'accepted'
            
            # Проверяем, набралось ли нужное количество волонтёров
            if self.volunteers_count >= self.required_volunteers:
                # Автоматически отклоняем все оставшиеся заявки
                pending_registrations = self.get_pending_volunteers()
                for pending_reg in pending_registrations:
                    pending_reg.status = 'rejected'
            
            db.session.commit()
            return True
        return False
    
    def reject_volunteer(self, registration_id):
        """Отклоняет заявку волонтёра"""
        registration = VolunteerRegistration.query.get(registration_id)
        if registration and registration.status == 'pending':
            registration.status = 'rejected'
            db.session.commit()
            return True
        return False

class VolunteerRegistration(db.Model):
    __tablename__ = 'volunteer_registration'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Внешние ключи с каскадным удалением
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Дополнительные поля
    contact_info = db.Column(db.String(200), nullable=False)
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')
    
    # Уникальный constraint чтобы один волонтер не мог дважды зарегистрироваться на одно мероприятие
    __table_args__ = (db.UniqueConstraint('event_id', 'volunteer_id', name='unique_event_volunteer'),)

# Перенесем функцию sanitize_html прямо в models.py
def sanitize_html(html_content):
    """Очистка HTML контента от потенциально опасных тегов"""
    import bleach
    
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
        'pre', 'a', 'img', 'div', 'span'
    ]
    allowed_attributes = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title'],
        '*': ['class']
    }
    
    return bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))