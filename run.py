from app import create_app, db
from app.models import User, Role, Event, VolunteerRegistration

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Role': Role, 
        'Event': Event, 
        'VolunteerRegistration': VolunteerRegistration
    }

if __name__ == '__main__':
    app.run(debug=True)