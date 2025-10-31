import sys
import os

# Добавляем корневую папку в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__), 'app')))

from app import app, db
from app.models import Role, User, Event, VolunteerRegistration
from datetime import date, timedelta

with app.app_context():
    # Полностью пересоздаем базу данных с каскадными связями
    print("Удаляем старую базу данных...")
    db.drop_all()
    
    print("Создаем новую базу данных с каскадными связями...")
    db.create_all()
    
    # Создание ролей
    roles = [
        Role(name='administrator', description='Суперпользователь, полный доступ'),
        Role(name='moderator', description='Может редактировать мероприятия'),
        Role(name='user', description='Может просматривать и регистрироваться')
    ]
    
    for role in roles:
        db.session.add(role)
    
    db.session.commit()
    print("Роли созданы")
    
    # Создание пользователей
    admin = User(
        login='admin',
        last_name='Иванов',
        first_name='Алексей',
        role_id=1
    )
    admin.set_password('admin123')
    
    moderator = User(
        login='moderator',
        last_name='Петрова',
        first_name='Мария',
        role_id=2
    )
    moderator.set_password('mod123')
    
    volunteer = User(
        login='volunteer',
        last_name='Сидоров',
        first_name='Иван',
        role_id=3
    )
    volunteer.set_password('vol123')
    
    db.session.add_all([admin, moderator, volunteer])
    db.session.commit()
    print("Пользователи созданы")
    
    # Создание мероприятий
    events = []
    for i in range(5):  # Создаем 5 мероприятий для теста
        event = Event(
            title=f'Тестовое мероприятие {i+1}',
            description=f'Описание тестового мероприятия {i+1}. Это мероприятие предназначено для тестирования функционала системы поиска волонтёров.',
            date=date.today() + timedelta(days=i*7),
            location=f'Место проведения {i+1}',
            required_volunteers=3 + i,
            image_filename='default_event.jpg',
            organizer_id=1 if i % 2 == 0 else 2
        )
        events.append(event)
    
    db.session.add_all(events)
    db.session.commit()
    print("Мероприятия созданы")
    
    print("\n" + "="*50)
    print("База данных успешно пересоздана с каскадными связями!")
    print("Тестовые данные:")
    print("Администратор: логин 'admin', пароль 'admin123'")
    print("Модератор: логин 'moderator', пароль 'mod123'")
    print("Пользователь: логин 'volunteer', пароль 'vol123'")
    print("="*50)