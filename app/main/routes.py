from flask import render_template, request, current_app
from flask_login import current_user
from datetime import date
from app.main import bp
from app.models import Event

@bp.route('/')
@bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Получаем только будущие мероприятия, отсортированные по дате (сначала новые)
    events_query = Event.query.filter(Event.date >= date.today()).order_by(Event.date.asc())
    
    # Пагинация
    events = events_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('main/index.html', events=events)