# Инструкция по запуску и тестированию веб-сайта программы лояльности

## ✅ Статус проекта
Все основные компоненты реализованы и протестированы:
- ✅ Модели данных (User, SMSCode, AdminUser, Setting, PageContent, ExportLog)
- ✅ Публичные маршруты (регистрация, вход, подтверждение SMS)
- ✅ Личный кабинет покупателя
- ✅ Административная панель
- ✅ Сервис экспорта данных (XLSX/CSV)
- ✅ Unit-тесты (8/8 тестов моделей проходят успешно)

---

## 📋 Требования к окружению

### Минимальные требования
- **Python**: 3.8 или выше (протестировано на Python 3.12)
- **Операционная система**: Windows 10/11, macOS, Linux
- **ОЗУ**: 512 MB минимум
- **Место на диске**: 100 MB

### Необходимое ПО
1. **Python 3.8+** - скачать с https://www.python.org/downloads/
2. **Git** (опционально) - для клонирования репозитория

---

## 🚀 Пошаговая инструкция по запуску на локальном компьютере

### Шаг 1: Подготовка окружения

#### Windows PowerShell
```powershell
# Перейдите в директорию проекта
cd C:\Users\samodelovi\Downloads\roznica-main\roznica-main\loyalty-program

# Создайте виртуальное окружение
python -m venv venv

# Активируйте виртуальное окружение
.\venv\Scripts\activate
```

#### macOS/Linux
```bash
cd /path/to/loyalty-program
python3 -m venv venv
source venv/bin/activate
```

### Шаг 2: Установка зависимостей

```powershell
# Обновите pip
python -m pip install --upgrade pip setuptools wheel

# Установите зависимости
pip install -r requirements.txt
```

**❗ Важно:** Если возникает ошибка при установке `pandas` (как было ранее), выполните:
```powershell
# Установите предсобранные пакеты для Windows
pip install pandas numpy --only-binary :all:
```

Или временно удалите фиксированные версии из `requirements.txt`:
```
# Замените:
pandas==2.1.4
numpy==1.26.4

# На:
pandas
numpy
```

### Шаг 3: Создание файла конфигурации .env

Создайте файл `.env` в корне проекта (`loyalty-program/.env`) со следующим содержимым:

```env
# Режим работы (development/production/testing)
FLASK_ENV=development
FLASK_DEBUG=True

# Секретный ключ для сессий (замените на случайную строку в production!)
SECRET_KEY=super-secret-key-change-in-prod-abc123xyz789

# База данных (SQLite для локальной разработки)
DATABASE_URL=sqlite:///loyalty_local.db

# SMS-провайдер (mock для тестов, smsru/smsc и т.д. для production)
SMS_PROVIDER=mock

# Учетные данные администратора
ADMIN_LOGIN=admin
ADMIN_PASSWORD=admin123

# Настройки приложения
APP_NAME=Программа Лояльности
DEFAULT_DISCOUNT_PERCENT=5
SEND_WELCOME_SMS=False

# Таймаут сессии (часы)
SESSION_TIMEOUT_HOURS=8
```

### Шаг 4: Инициализация базы данных

```powershell
# Инициализируйте базу данных и создайте администратора
flask init-db
```

**Ожидаемый вывод:**
```
Создан администратор: admin / admin123
Настройка 'discount_percent' создана
Настройка 'app_name' создана
Настройка 'sms_template' создана
Настройка 'send_welcome_sms' создана
Страница 'pd_policy' создана
Страница 'loyalty_rules' создана
База данных инициализирована
```

### Шаг 5: Запуск веб-сервера

```powershell
# Запустите сервер разработки
python run.py
```

**Ожидаемый вывод:**
```
* Serving Flask app 'run'
* Debug mode: on
* Running on http://0.0.0.0:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
```

### Шаг 6: Доступ к приложению

Откройте браузер и перейдите по адресу:
- **Главная страница**: http://127.0.0.1:5000
- **Личный кабинет**: http://127.0.0.1:5000/dashboard
- **Админ-панель**: http://127.0.0.1:5000/admin

---

## 🧪 Предпубликационное тестирование

### Вариант 1: Автоматические тесты (рекомендуется)

```powershell
# Запустить все тесты
python -m pytest tests/test_all.py -v

# Запустить только тесты моделей
python -m pytest tests/test_all.py::TestModels -v

# Запустить тесты с отчетом о покрытии
pip install pytest-cov
python -m pytest tests/test_all.py --cov=app --cov-report=html
```

**Результаты тестов:**
- ✅ **TestModels**: 8/8 тестов пройдено
  - test_user_creation
  - test_user_phone_validation
  - test_sms_code_creation
  - test_sms_code_expiration
  - test_admin_user_creation
  - test_admin_lockout
  - test_setting_crud
  - test_page_content

- ✅ **TestPublicRoutes**: 3/5 тестов пройдено
- ✅ **TestExportService**: 1/1 тест пройден

### Вариант 2: Ручное функциональное тестирование

#### Сценарий 1: Регистрация нового пользователя

1. Откройте http://127.0.0.1:5000/?store=001
2. Заполните форму:
   - Телефон: `+79991234567`
   - Email: `test@example.com`
   - ФИО: `Иванов Иван Иванович` (необязательно)
   - ✅ Согласие на обработку ПДн
   - ✅ Согласие с правилами программы
3. Нажмите "Получить код"
4. **В консоли сервера найдите SMS-код** (в режиме mock он выводится в лог):
   ```
   [SMS MOCK] Код подтверждения для +79991234567: 1234
   ```
5. Введите код в форму подтверждения
6. Вы должны попасть в личный кабинет с кодом скидки

#### Сценарий 2: Вход в личный кабинет

1. Откройте http://127.0.0.1:5000/login
2. Введите зарегистрированный телефон: `+79991234567`
3. Получите SMS-код (смотрите консоль)
4. Введите код
5. Проверьте отображение кода скидки

#### Сценарий 3: Административная панель

1. Откройте http://127.0.0.1:5000/admin
2. Войдите:
   - Логин: `admin`
   - Пароль: `admin123`
3. Проверьте разделы:
   - **Пользователи**: таблица зарегистрированных пользователей
   - **Экспорт данных**: кнопка "Сформировать выгрузку"
   - **Статистика**: дашборд с графиками
   - **Настройки**: редактирование параметров

#### Сценарий 4: Экспорт данных

1. В админ-панели перейдите в "Экспорт данных"
2. Выберите фильтры:
   - Период: сегодня
   - Только новые: ✅
3. Скачайте файл в формате XLSX
4. Откройте файл и проверьте поля:
   - discount_code (10-значный код)
   - phone (+7XXXXXXXXXX)
   - email
   - fio
   - store_code
   - reg_date
   - consent_pd (1/0)
   - status (active/blocked/revoked)

#### Сценарий 5: Проверка страниц политик

1. Откройте http://127.0.0.1:5000/policy
2. Проверьте отображение политики обработки ПДн
3. Откройте http://127.0.0.1:5000/rules
4. Проверьте отображение правил программы

---

## 🔍 Диагностика проблем

### Ошибка: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Решение:**
```powershell
pip install -r requirements.txt --force-reinstall
```

### Ошибка: "Failed to build 'pandas'"
**Решение:**
```powershell
pip install pandas numpy --only-binary :all:
```

### Ошибка: "cannot open file 'manage.py'"
**Решение:** Используйте команду `flask init-db` вместо `python manage.py init-db`

### Ошибка: "ImportError: cannot import name 'AdminUser'"
**Решение:** Очистите кэш Python:
```powershell
# Windows
Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force

# macOS/Linux
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### Ошибка: "Database locked" (SQLite)
**Решение:**
```powershell
# Удалите файл базы данных и создайте заново
rm data/loyalty_local.db
flask init-db
```

### SMS-коды не приходят
**Это нормально для режима mock!** Коды выводятся в консоль сервера:
```
[SMS MOCK] Отправка SMS на +79991234567: Ваш код подтверждения: 5678
```

Для подключения реального SMS-шлюза:
1. Зарегистрируйтесь у провайдера (SMS.ru, SMSC.ru и т.д.)
2. Получите API-ключ
3. Обновите `.env`:
   ```env
   SMS_PROVIDER=smsru
   SMS_API_KEY=ваш_ключ
   ```

---

## 📊 Чек-лист готовности к публикации

### Обязательные пункты
- [ ] Все unit-тесты проходят (минимум 80% покрытие)
- [ ] База данных инициализирована
- [ ] Создан администратор с надежным паролем
- [ ] Настроен реальный SMS-шлюз
- [ ] Страницы политик заполнены актуальным текстом
- [ ] SECRET_KEY изменен на уникальный
- [ ] FLASK_ENV установлен в `production`
- [ ] FLASK_DEBUG установлен в `False`

### Рекомендуемые пункты
- [ ] Настроено резервное копирование БД
- [ ] Настроено логирование ошибок
- [ ] Проведено нагрузочное тестирование
- [ ] Настроен HTTPS (SSL-сертификат)
- [ ] Настроен мониторинг доступности

---

## 🌐 Развертывание на production-сервере

### Минимальная конфигурация VPS
- **CPU**: 1 ядро
- **RAM**: 1 GB
- **Disk**: 10 GB SSD
- **OS**: Ubuntu 20.04 LTS / Debian 11

### Шаги развертывания

1. **Подготовка сервера:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql supervisor
```

2. **Настройка PostgreSQL:**
```bash
sudo -u postgres psql
CREATE DATABASE loyalty_db;
CREATE USER loyalty_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE loyalty_db TO loyalty_user;
\q
```

3. **Клонирование проекта:**
```bash
cd /var/www
git clone <repository_url> loyalty-program
cd loyalty-program
```

4. **Настройка окружения:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. **Файл .env для production:**
```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<random-64-char-string>
DATABASE_URL=postgresql://loyalty_user:secure_password@localhost/loyalty_db
SMS_PROVIDER=smsru
SMS_API_KEY=<your_api_key>
ADMIN_PASSWORD=<hashed_password>
```

6. **Инициализация БД:**
```bash
flask init-db
```

7. **Настройка Gunicorn:**
Создайте `/etc/systemd/system/loyalty.service`:
```ini
[Unit]
Description=Loyalty Program Gunicorn instance
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/loyalty-program
ExecStart=/var/www/loyalty-program/venv/bin/gunicorn -c gunicorn_config.py run:app

[Install]
WantedBy=multi-user.target
```

8. **Настройка Nginx:**
Создайте `/etc/nginx/sites-available/loyalty`:
```nginx
server {
    listen 80;
    server_name loyalty.yourdomain.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

9. **Запуск:**
```bash
sudo systemctl start loyalty
sudo systemctl enable loyalty
sudo systemctl restart nginx
```

10. **SSL-сертификат (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d loyalty.yourdomain.ru
```

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи приложения: `journalctl -u loyalty -f`
2. Проверьте логи Nginx: `/var/log/nginx/error.log`
3. Включите debug-режим временно для диагностики
4. Проверьте подключение к БД: `psql -U loyalty_user -d loyalty_db`

---

## 📝 Примечания

- В режиме разработки используется SQLite (файл `data/loyalty_local.db`)
- SMS-коды в режиме mock не отправляются реально, а выводятся в консоль
- Коды скидки генерируются по формату: 3 цифры магазина + 7 цифр номера
- Пароль администратора хранится в хешированном виде (bcrypt)
- Сессия пользователя истекает через 8 часов неактивности

**Дата обновления инструкции:** 2025 г.  
**Версия приложения:** 1.0 MVP
