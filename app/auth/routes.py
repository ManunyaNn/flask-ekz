from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user
from app.auth import bp
from app.auth.forms import LoginForm
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже аутентифицирован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Ищем пользователя по логину
        user = User.query.filter_by(login=form.login.data).first()
        
        # Проверяем пользователя и пароль
        if user is None or not user.check_password(form.password.data):
            flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Выполняем вход
        login_user(user, remember=form.remember_me.data)
        
        # Перенаправляем на следующую страницу или на главную
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        
        flash(f'Добро пожаловать, {user.full_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('main.index'))