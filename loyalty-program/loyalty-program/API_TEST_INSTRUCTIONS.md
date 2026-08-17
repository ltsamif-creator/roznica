# Инструкция по тестированию API

## 1. Подготовка

### Запуск приложения
```bash
cd /workspace/loyalty-program
python run.py
```
Приложение будет доступно по адресу: http://localhost:5000

### Создание администратора (если нет)
```bash
cd /workspace/loyalty-program
python << 'PYEOF'
from app import db, create_app
from app.models import AdminUser
import bcrypt

app = create_app()
with app.app_context():
    admin = AdminUser.query.filter_by(username='admin').first()
    if not admin:
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = AdminUser(
            username='admin',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Администратор создан: admin / admin123")
    else:
        print("Администратор уже существует")
PYEOF
```

---

## 2. API для получения новых пользователей

### GET /admin/api/new-users

**Описание:** Получение списка всех новых зарегистрированных покупателей (не экспортированных)

**Требования:** Требуется авторизация администратора

**Параметры:**
- `days` (опционально) - количество дней для фильтрации

**Пример запроса через curl:**

```bash
# Шаг 1: Логин администратора и получение cookie
curl -c cookies.txt -X POST http://localhost:5000/admin/login \
  -d "username=admin" -d "password=admin123"

# Шаг 2: Получение новых пользователей
curl -b cookies.txt http://localhost:5000/admin/api/new-users | python -m json.tool

# С фильтром по дням (только за последние 7 дней)
curl -b cookies.txt "http://localhost:5000/admin/api/new-users?days=7" | python -m json.tool
```

**Пример ответа:**
```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "discount_code": "0010000001",
      "phone": "+79991234567",
      "email": "test@example.com",
      "fio": "Тест Пользователь",
      "store_code": "001",
      "status": "active",
      "consent_pd": true,
      "consent_pd_date": "2025-01-15T10:30:00",
      "consent_marketing": false,
      "created_at": "2025-01-15T10:30:00",
      "is_exported": false,
      "exported_at": null
    }
  ],
  "total_count": 1
}
```

---

## 3. API для импорта чеков покупателей

### POST /admin/api/purchases/import

**Описание:** Импорт массива чеков покупателей в базу данных

**Требования:** Требуется авторизация администратора

**Формат запроса (JSON):**
```json
{
  "purchases": [
    {
      "discount_code": "0010000001",
      "receipt_number": "R001234567",
      "store_code": "001",
      "total_amount": 500000,
      "discount_amount": 25000,
      "purchase_date": "2025-01-15T10:30:00",
      "items": [
        {"name": "Товар 1", "price": 25000, "quantity": 2},
        {"name": "Товар 2", "price": 10000, "quantity": 3}
      ]
    }
  ]
}
```

**Поля:**
- `discount_code` (обязательно) - код скидки покупателя (10 цифр)
- `receipt_number` (обязательно) - номер чека (уникальный)
- `store_code` (обязательно) - код магазина (3 символа)
- `total_amount` (обязательно) - сумма чека в копейках
- `discount_amount` (опционально) - сумма скидки в копейках
- `purchase_date` (обязательно) - дата покупки (ISO формат или YYYY-MM-DD HH:MM:SS)
- `items` (опционально) - массив товаров

**Пример запроса через curl:**

```bash
# Создаем JSON файл с данными
cat > purchases.json << 'JSONEOF'
{
  "purchases": [
    {
      "discount_code": "0010000001",
      "receipt_number": "R001234567",
      "store_code": "001",
      "total_amount": 500000,
      "discount_amount": 25000,
      "purchase_date": "2025-01-15T10:30:00",
      "items": [
        {"name": "Молоко", "price": 8900, "quantity": 2},
        {"name": "Хлеб", "price": 5500, "quantity": 3}
      ]
    },
    {
      "discount_code": "0010000001",
      "receipt_number": "R001234568",
      "store_code": "001",
      "total_amount": 150000,
      "discount_amount": 7500,
      "purchase_date": "2025-01-16T14:20:00"
    }
  ]
}
JSONEOF

# Отправляем запрос на импорт
curl -b cookies.txt -X POST http://localhost:5000/admin/api/purchases/import \
  -H "Content-Type: application/json" \
  -d @purchases.json | python -m json.tool
```

**Пример успешного ответа:**
```json
{
  "success": true,
  "imported_count": 2,
  "errors": null
}
```

**Пример ответа с ошибками:**
```json
{
  "success": true,
  "imported_count": 1,
  "errors": [
    "Запись 0: пользователь с кодом 9999999999 не найден",
    "Запись 1: чек R001234567 уже существует"
  ]
}
```

---

## 4. API для получения истории покупок пользователя

### GET /dashboard/api/purchases

**Описание:** Получение всех покупок текущего авторизованного пользователя

**Требования:** Требуется авторизация пользователя (покупателя)

**Пример запроса через curl:**

```bash
# Шаг 1: Логин пользователя
curl -c user_cookies.txt -X POST http://localhost:5000/login \
  -d "phone=+79991234567"

# Шаг 2: Получение истории покупок
curl -b user_cookies.txt http://localhost:5000/dashboard/api/purchases | python -m json.tool
```

**Пример ответа:**
```json
{
  "success": true,
  "purchases": [
    {
      "id": 1,
      "user_id": 1,
      "receipt_number": "R001234567",
      "store_code": "001",
      "total_amount": 500000,
      "discount_amount": 25000,
      "purchase_date": "2025-01-15T10:30:00",
      "items": [
        {"name": "Молоко", "price": 8900, "quantity": 2},
        {"name": "Хлеб", "price": 5500, "quantity": 3}
      ],
      "created_at": "2025-01-15T10:35:00"
    }
  ],
  "total_count": 1
}
```

---

## 5. Тестирование через веб-интерфейс

### Страница истории покупок
1. Залогиньтесь как пользователь: http://localhost:5000/login
2. Перейдите в личный кабинет: http://localhost:5000/dashboard
3. Нажмите кнопку "История покупок"
4. Отобразится страница со всеми покупками пользователя

### Админ-панель для API тестирования
1. Залогиньтесь как администратор: http://localhost:5000/admin/login
   - Логин: `admin`
   - Пароль: `admin123`
2. Для тестирования API используйте инструменты:
   - **Postman**
   - **Insomnia**
   - **curl** (как показано выше)

---

## 6. Быстрый скрипт для тестирования

Создайте файл `test_api.py`:

```python
#!/usr/bin/env python3
"""Скрипт для быстрого тестирования API"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_api():
    session = requests.Session()
    
    # 1. Логин администратора
    print("=== Логин администратора ===")
    resp = session.post(f'{BASE_URL}/admin/login', 
                        data={'username': 'admin', 'password': 'admin123'})
    print(f"Статус: {resp.status_code}")
    
    # 2. Получение новых пользователей
    print("\n=== Получение новых пользователей ===")
    resp = session.get(f'{BASE_URL}/admin/api/new-users')
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 3. Импорт покупок
    print("\n=== Импорт покупок ===")
    purchases_data = {
        "purchases": [
            {
                "discount_code": "0010000001",
                "receipt_number": f"TEST_{i}",
                "store_code": "001",
                "total_amount": 100000,
                "discount_amount": 5000,
                "purchase_date": "2025-01-15T10:30:00",
                "items": [{"name": f"Товар {i}", "price": 5000, "quantity": 2}]
            }
            for i in range(3)
        ]
    }
    resp = session.post(f'{BASE_URL}/admin/api/purchases/import',
                        json=purchases_data)
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 4. Логин пользователя
    print("\n=== Логин пользователя ===")
    user_session = requests.Session()
    resp = user_session.post(f'{BASE_URL}/login',
                             data={'phone': '+79991234567'})
    print(f"Статус: {resp.status_code}")
    
    # 5. Получение истории покупок
    print("\n=== История покупок ===")
    resp = user_session.get(f'{BASE_URL}/dashboard/api/purchases')
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    test_api()
```

Запуск:
```bash
python test_api.py
```

---

## 7. Проверка целостности работы

```bash
cd /workspace/loyalty-program
python -m pytest tests/test_all.py -v
```

Все 30 тестов должны пройти успешно ✓
