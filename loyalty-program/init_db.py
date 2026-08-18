"""
Скрипт инициализации базы данных.
Создает все необходимые таблицы согласно моделям.
Запускать при первом развертывании или после очистки БД.
"""
import sys
import os

# Добавляем корень проекта в путь, чтобы работали импорты
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from config import Config

def init_database():
    app = create_app()
    
    with app.app_context():
        print("Подключение к базе данных...")
        # Создаем все таблицы, определенные в моделях
        db.create_all()
        print("Таблицы успешно созданы!")
        
        # Проверка наличия таблиц
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Существующие таблицы: {', '.join(tables)}")

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
