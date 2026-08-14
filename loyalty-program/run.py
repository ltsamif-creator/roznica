#!/usr/bin/env python3
"""
Точка входа приложения
Запуск веб-сервера Flask
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from app import create_app, db
from app.models import AdminUser, Setting, PageContent
import bcrypt

app = create_app()


@app.cli.command('init-db')
def init_db_command():
    """Инициализация базы данных"""
    db.create_all()
    
    # Создаем администратора по умолчанию
    admin = AdminUser.query.filter_by(username='admin').first()
    if not admin:
        # Хешируем пароль из .env или используем дефолтный
        password_hash_env = os.environ.get('ADMIN_PASSWORD_HASH', '')
        
        if password_hash_env:
            password_hash = password_hash_env
        else:
            # Если хеш не указан, создаем с паролем 'admin123'
            password = 'admin123'
            password_hash = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt(rounds=12)
            ).decode('utf-8')
            print(f"Создан администратор: admin / {password}")
        
        admin = AdminUser(
            username='admin',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        print("Администратор создан")
    
    # Создаем настройки по умолчанию
    default_settings = {
        'discount_percent': ('5', 'Размер скидки постоянного покупателя в процентах'),
        'app_name': ('Программа Лояльности', 'Название программы лояльности'),
        'sms_template': ('Ваш код подтверждения: {code}. Действует 5 минут.', 'Шаблон SMS с кодом подтверждения'),
        'send_welcome_sms': ('1', 'Отправлять приветственное SMS после регистрации (1/0)'),
    }
    
    for key, (value, description) in default_settings.items():
        existing = Setting.query.filter_by(key=key).first()
        if not existing:
            setting = Setting(
                key=key,
                value=value,
                description=description
            )
            db.session.add(setting)
            print(f"Настройка '{key}' создана")
    
    # Создаем страницы по умолчанию
    default_pages = [
        {
            'page_key': 'pd_policy',
            'title': 'Политика обработки персональных данных',
            'content': '''<h2>1. Общие положения</h2>
<p>Настоящая Политика обработки персональных данных (далее – Политика) действует в отношении всех персональных данных, которые могут быть получены Оператором в процессе использования Пользователем веб-сайта.</p>

<h2>2. Цели обработки персональных данных</h2>
<p>Обработка персональных данных осуществляется в целях:</p>
<ul>
<li>Регистрации пользователя в программе лояльности;</li>
<li>Предоставления пользователю доступа к личному кабинету;</li>
<li>Информирования о статусе участия в программе лояльности;</li>
<li>Выполнения требований законодательства РФ.</li>
</ul>

<h2>3. Состав персональных данных</h2>
<p>Обрабатываются следующие персональные данные:</p>
<ul>
<li>Номер телефона;</li>
<li>Адрес электронной почты;</li>
<li>ФИО (по желанию);</li>
<li>Дата и время регистрации;</li>
<li>Код магазина регистрации.</li>
</ul>

<h2>4. Правовые основания</h2>
<p>Обработка осуществляется на основании согласия субъекта персональных данных.</p>

<h2>5. Меры защиты</h2>
<p>Оператор принимает необходимые технические и организационные меры для защиты персональных данных.</p>''',
            'version': '1.0'
        },
        {
            'page_key': 'loyalty_rules',
            'title': 'Правила программы лояльности',
            'content': '''<h2>1. Общие положения</h2>
<p>1.1. Программа лояльности предназначена для поощрения постоянных покупателей.</p>
<p>1.2. Участие в Программе является добровольным.</p>

<h2>2. Условия участия</h2>
<p>2.1. Для участия необходимо зарегистрироваться через веб-сайт.</p>
<p>2.2. Регистрация доступна гражданам РФ старше 18 лет.</p>
<p>2.3. Один пользователь может иметь только одну учетную запись.</p>

<h2>3. Скидка постоянного покупателя</h2>
<p>3.1. Зарегистрированным пользователям предоставляется скидка в размере, указанном на сайте.</p>
<p>3.2. Скидка применяется при предъявлении кода из личного кабинета.</p>
<p>3.3. Скидка не суммируется с другими акционными предложениями.</p>

<h2>4. Права и обязанности</h2>
<p>4.1. Участник вправе отозвать согласие на обработку персональных данных в любой момент.</p>
<p>4.2. При отзыве согласия участие в Программе прекращается.</p>

<h2>5. Изменение правил</h2>
<p>5.1. Организатор вправе изменять Правила с публикацией на сайте.</p>''',
            'version': '1.0'
        }
    ]
    
    for page_data in default_pages:
        existing = PageContent.query.filter_by(
            page_key=page_data['page_key'], 
            is_active=True
        ).first()
        if not existing:
            page = PageContent(**page_data)
            db.session.add(page)
            print(f"Страница '{page_data['page_key']}' создана")
    
    db.session.commit()
    print("База данных инициализирована")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
