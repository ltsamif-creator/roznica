from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Ищем по email
    user = User.query.filter_by(email='admin@local.ru').first()
    
    if not user:
        print("Пользователь не найден, создаем...")
        user = User(
            discount_code='1000000001',  # Обязательное поле: 10 цифр
            phone='+79990000000',
            email='admin@local.ru',
            fio='Администратор Системы',
            store_code='ADMIN',
            status='active',
            consent_pd=True,
            consent_pd_date='2026-08-17',
            consent_pd_version='1.0',
            is_exported=True  # Чтобы не попадал в выгрузку новых
        )
        db.session.add(user)
    else:
        print(f"Пользователь найден: {user.email}")
    
    # Устанавливаем пароль
    user.set_password('admin123')
    db.session.commit()
    print("SUCCESS: Вход: admin@local.ru / Пароль: admin123")