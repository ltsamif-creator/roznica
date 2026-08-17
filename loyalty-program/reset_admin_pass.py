from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if user:
        user.set_password('admin123')
        db.session.commit()
        print("Пароль администратора успешно установлен на: admin123")
    else:
        print("Пользователь admin не найден!")