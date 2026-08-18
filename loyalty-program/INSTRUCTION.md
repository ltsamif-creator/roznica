# Инструкция по запуску приложения "Программа Лояльности"

## Требования к системе

- Python 3.8 или выше
- pip (менеджер пакетов Python)
- Git (для клонирования репозитория)

## Шаг 1: Клонирование репозитория

```bash
git clone <URL_репозитория>
cd loyalty-program
```

## Шаг 2: Создание виртуального окружения

### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

## Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 4: Настройка переменных окружения

1. Скопируйте файл `.env` в `.env.local` (не отслеживается git):
   ```bash
   cp .env .env.local
   ```

2. Отредактируйте `.env.local` и измените следующие параметры:
   - `SECRET_KEY` — установите уникальный секретный ключ для продакшена
   - `ADMIN_PASSWORD_HASH` — сгенерируйте новый хеш пароля для администратора
   - `SMS_API_URL` и `SMS_API_KEY` — настройте ваш SMS-шлюз
   - `FLASK_ENV` — установите `production` для продакшена

### Генерация SECRET_KEY:
```python
import secrets
print(secrets.token_hex(32))
```

### Генерация хеша пароля администратора:
```python
import bcrypt
password = "ваш_пароль"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(hashed.decode('utf-8'))
```

## Шаг 5: Инициализация базы данных

При первом запуске база данных создастся автоматически. Если нужно создать вручную:

```bash
python run.py
```

Затем перейдите в браузере на `http://localhost:5000` — приложение само инициализирует БД при первом запросе.

## Шаг 6: Запуск приложения

### Режим разработки:
```bash
python run.py
```

Или через Flask CLI:
```bash
flask run
```

Приложение будет доступно по адресу: `http://127.0.0.1:5000`

### Режим продакшена (рекомендуется с Gunicorn):

Установите Gunicorn:
```bash
pip install gunicorn
```

Запустите:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

## Шаг 7: Вход в систему

- **URL для входа**: `http://localhost:5000/login`
- **Логин по умолчанию**: `admin`
- **Пароль по умолчанию**: см. значение `ADMIN_PASSWORD` в `.env` (или установите свой)

## Проверка работы

1. Откройте браузер и перейдите на `http://localhost:5000`
2. Войдите под учётной записью администратора
3. Проверьте разделы:
   - Управление клиентами
   - Генерация промокодов
   - Статистика
   - Экспорт данных

## Запуск тестов

```bash
pytest tests/
```

## Решение проблем

### Ошибка "Database not found":
Убедитесь, что папка `instance/` существует и имеет права на запись.

### Ошибка "Module not found":
Проверьте, что виртуальное окружение активировано и все зависимости установлены:
```bash
pip install -r requirements.txt
```

### Ошибка порта "Address already in use":
Освободите порт 5000 или запустите на другом порту:
```bash
export FLASK_RUN_PORT=5001  # Linux/macOS
set FLASK_RUN_PORT=5001     # Windows
flask run
```

## Дополнительные команды

### Создать нового администратора:
```bash
python -c "from app import create_app, db; from app.models import User; import bcrypt; app = create_app(); ctx = app.app_context(); ctx.push(); user = User(username='newadmin', password_hash=bcrypt.hashpw('password'.encode(), bcrypt.gensalt()).decode(), role='admin'); db.session.add(user); db.session.commit()"
```

### Сбросить базу данных (осторожно!):
```bash
rm instance/loyalty.db
python run.py
```

## Структура проекта

```
loyalty-program/
├── app/                  # Основной код приложения
│   ├── models.py         # Модели базы данных
│   ├── routes.py         # Маршруты (endpoints)
│   ├── forms.py          # Формы WTForms
│   ├── services.py       # Бизнес-логика
│   ├── templates/        # HTML-шаблоны
│   └── static/           # CSS, JS, изображения
├── config/               # Конфигурационные файлы
├── instance/             # База данных и файлы экземпляра
├── tests/                # Тесты
├── .env                  # Переменные окружения (не коммитить!)
├── .gitignore            # Игнорируемые файлы Git
├── requirements.txt      # Зависимости Python
└── run.py                # Точка входа приложения
```

## Безопасность

⚠️ **Важно перед деплоем:**
1. Измените `SECRET_KEY` на уникальный
2. Смените пароль администратора
3. Установите `FLASK_ENV=production`
4. Настройте HTTPS
5. Ограничьте доступ к админ-панели по IP (опционально)
6. Регулярно обновляйте зависимости

## Поддержка

При возникновении проблем проверьте логи приложения в файле `server.log` (если настроено логирование).
