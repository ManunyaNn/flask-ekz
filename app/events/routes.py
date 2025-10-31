from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from app.events import bp
from app.events.forms import EventForm, EventEditForm, VolunteerRegistrationForm
from app.models import Event, VolunteerRegistration, db
from app.utils import save_image, sanitize_html

@bp.route('/')
def event_list():
    return redirect(url_for('main.index'))

@bp.route('/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Получаем регистрацию текущего пользователя (если есть)
    user_registration = None
    if current_user.is_authenticated:
        user_registration = event.get_user_registration(current_user.id)
    
    # Форма для регистрации
    form = VolunteerRegistrationForm()
    
    return render_template('events/event_detail.html', 
                         event=event, 
                         user_registration=user_registration,
                         form=form)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_event():
    # Проверка прав - только администратор
    if current_user.role.name != 'administrator':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('main.index'))
    
    form = EventForm()
    
    if form.validate_on_submit():
        try:
            # Сохраняем изображение
            image_filename = None
            if form.image.data:
                image_filename = save_image(form.image.data)
                if not image_filename:
                    flash('Ошибка при загрузке изображения', 'danger')
                    return render_template('events/event_new.html', form=form)
            
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
            return redirect(url_for('events.event_detail', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating event: {e}')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
    
    return render_template('events/event_new.html', form=form)

@bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('main.index'))
    
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
            return redirect(url_for('events.event_detail', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating event: {e}')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
    
    return render_template('events/event_edit.html', form=form, event=event)

@bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    # Проверка прав - только администратор
    if current_user.role.name != 'administrator':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('main.index'))
    
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
        current_app.logger.error(f"Error deleting event: {e}")
    
    return redirect(url_for('main.index'))

@bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = VolunteerRegistrationForm()
    
    # Проверяем, что пользователь еще не зарегистрирован
    existing_registration = event.get_user_registration(current_user.id)
    if existing_registration:
        flash('Вы уже зарегистрированы на это мероприятие', 'warning')
        return redirect(url_for('events.event_detail', event_id=event.id))
    
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
    
    return redirect(url_for('events.event_detail', event_id=event.id))

@bp.route('/<int:event_id>/registration/<int:registration_id>/accept')
@login_required
def accept_registration(event_id, registration_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    event = Event.query.get_or_404(event_id)
    
    if event.accept_volunteer(registration_id):
        flash('Заявка волонтёра принята', 'success')
    else:
        flash('Не удалось принять заявку', 'danger')
    
    return redirect(url_for('events.event_detail', event_id=event_id))

@bp.route('/<int:event_id>/registration/<int:registration_id>/reject')
@login_required
def reject_registration(event_id, registration_id):
    # Проверка прав - только администратор и модератор
    if current_user.role.name not in ['administrator', 'moderator']:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    event = Event.query.get_or_404(event_id)
    
    if event.reject_volunteer(registration_id):
        flash('Заявка волонтёра отклонена', 'info')
    else:
        flash('Не удалось отклонить заявку', 'danger')
    
    return redirect(url_for('events.event_detail', event_id=event_id))