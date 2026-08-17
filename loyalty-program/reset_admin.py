from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Ищем админа по email (или создаем если нет)
    user = User.query.filter_by(email='admin@local.ru').first()
    
    if not user:
        print("Пользователь admin@local.ru не найден, создаем...")
        user = User(
            email='admin@local.ru',
            fio='Администратор Системы',
            phone='+70000000000',
            discount_code='ADMIN001',
            is_exported=True  # Чтобы не попадал в выгрузку новых
        )
        db.session.add(user)
    
    user.set_password('admin123')
    user.is_admin = True  # Устанавливаем флаг администратора
    db.session.commit()
    
    print(f"SUCCESS: Пользователь ID={user.id} (email: admin@local.ru)")
    print(f"Логин: admin@local.ru")
    print(f"Пароль: admin123")
    print(f"Discount code: {user.discount_code}")
