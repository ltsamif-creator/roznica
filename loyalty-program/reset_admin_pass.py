#!/usr/bin/env python3
"""Скрипт для создания/сброса пароля администратора"""

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AdminUser

def generate_password_hash(password):
    """Генерация хэша пароля"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def reset_admin_password():
    app = create_app()
    
    with app.app_context():
        # Находим администратора
        admin = AdminUser.query.filter_by(username='admin').first()
        
        if not admin:
            print("Пользователь 'admin' не найден. Создаю нового...")
            admin = AdminUser(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_active=True
            )
            db.session.add(admin)
            print("Администратор создан!")
        else:
            print("Администратор найден. Обновляю пароль...")
        
        # Устанавливаем новый пароль
        new_password = 'admin123'
        admin.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        print("=" * 50)
        print("ПАРОЛЬ АДМИНИСТРАТОРА УСПЕШНО СБРОШЕН!")
        print("=" * 50)
        print(f"Логин: admin")
        print(f"Пароль: {new_password}")
        print("=" * 50)
        print("\nТеперь вы можете войти в панель администратора:")
        print("http://localhost:5000/admin/login")
        print("=" * 50)
        
        return True

if __name__ == '__main__':
    try:
        reset_admin_password()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
