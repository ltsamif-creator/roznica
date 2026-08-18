from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime, timedelta
import secrets
from ..models import db, User, SMSCode, PageContent, UserStatus, PasswordResetToken
from ..services import CodeGenerator, SMSService, ValidationService, RateLimiter

public_bp = Blueprint('public', __name__)

# Глобальный ограничитель запросов
rate_limiter = RateLimiter()


@public_bp.route('/')
def index():
    """Главная страница (лендинг)"""
    store_code = request.args.get('store', '001')
    
    # Получаем настройки
    app_name = current_app.config.get('APP_NAME', 'Программа Лояльности')
    discount_percent = current_app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)
    
    return render_template('public/index.html', 
                         store_code=store_code,
                         app_name=app_name,
                         discount_percent=discount_percent)


@public_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    store_code = request.args.get('store', '001')
    
    # Проверка rate limiting
    client_ip = request.remote_addr
    if not rate_limiter.is_allowed(client_ip, 'registration', max_requests=5, window_seconds=900):
        retry_after = rate_limiter.get_retry_after(client_ip, 'registration')
        flash(f'Слишком много попыток регистрации. Попробуйте через {retry_after // 60} мин.', 'error')
        return redirect(url_for('public.index'))
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        fio = request.form.get('fio', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        consent_pd = request.form.get('consent_pd') == 'on'
        consent_marketing = request.form.get('consent_marketing') == 'on'
        
        # Валидация телефона
        is_valid, result = ValidationService.validate_phone(phone)
        if not is_valid:
            flash(result, 'error')
            return render_template('public/register.html', 
                                 phone=phone, email=email, fio=fio,
                                 consent_pd=consent_pd, consent_marketing=consent_marketing,
                                 store_code=store_code)
        normalized_phone = result
        
        # Валидация email
        is_valid, result = ValidationService.validate_email(email)
        if not is_valid:
            flash(result, 'error')
            return render_template('public/register.html',
                                 phone=normalized_phone, email=email, fio=fio,
                                 consent_pd=consent_pd, consent_marketing=consent_marketing,
                                 store_code=store_code)
        normalized_email = result
        
        # Валидация пароля
        if len(password) < 6:
            flash('Пароль должен содержать не менее 6 символов', 'error')
            return render_template('public/register.html',
                                 phone=normalized_phone, email=normalized_email, fio=fio,
                                 consent_pd=consent_pd, consent_marketing=consent_marketing,
                                 store_code=store_code)
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('public/register.html',
                                 phone=normalized_phone, email=normalized_email, fio=fio,
                                 consent_pd=consent_pd, consent_marketing=consent_marketing,
                                 store_code=store_code)
        
        # Валидация ФИО
        is_valid, result = ValidationService.validate_fio(fio)
        if not is_valid:
            flash(result, 'error')
            return render_template('public/register.html',
                                 phone=normalized_phone, email=normalized_email, fio=fio,
                                 consent_pd=consent_pd, consent_marketing=consent_marketing,
                                 store_code=store_code)
        normalized_fio = result
        
        # Проверка согласий
        if not consent_pd:
            flash('Необходимо согласие на обработку персональных данных', 'error')
            return render_template('public/register.html',
                                 phone=normalized_phone, email=normalized_email, fio=normalized_fio,
                                 consent_marketing=consent_marketing,
                                 store_code=store_code)
        
        # Проверка, не зарегистрирован ли уже этот телефон
        existing_user_phone = User.query.filter_by(phone=normalized_phone).first()
        if existing_user_phone:
            flash('Этот номер телефона уже зарегистрирован', 'info')
            return redirect(url_for('public.login'))
        
        # Проверка, не зарегистрирован ли уже этот email
        existing_user_email = User.query.filter_by(email=normalized_email).first()
        if existing_user_email:
            flash('Этот e-mail уже зарегистрирован', 'info')
            return redirect(url_for('public.login'))
        
        # Генерация SMS-кода
        sms_code = CodeGenerator.generate_sms_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Сохраняем данные регистрации в сессии
        session['registration_data'] = {
            'phone': normalized_phone,
            'email': normalized_email,
            'fio': normalized_fio,
            'password': password,  # Временное хранение до подтверждения
            'store_code': store_code,
            'consent_pd': consent_pd,
            'consent_marketing': consent_marketing
        }
        session['sms_code'] = sms_code
        session['sms_code_expires'] = expires_at.timestamp()
        session['sms_purpose'] = 'registration'
        
        # Отправка SMS
        sms_service = current_app.extensions.get('sms_service')
        if sms_service:
            sms_service.send_verification_code(normalized_phone, sms_code, 'registration')
        
        flash('Код подтверждения отправлен на ваш телефон', 'success')
        return redirect(url_for('public.verify_sms'))
    
    return render_template('public/register.html', store_code=store_code)


@public_bp.route('/verify-sms', methods=['GET', 'POST'])
def verify_sms():
    """Страница подтверждения SMS-кода"""
    if 'registration_data' not in session and 'login_phone' not in session:
        flash('Сначала заполните форму', 'warning')
        return redirect(url_for('public.register'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        # Получаем данные из сессии
        expected_code = session.get('sms_code')
        expires_at = session.get('sms_code_expires', 0)
        purpose = session.get('sms_purpose', 'registration')
        
        # Проверка времени действия кода
        if datetime.utcnow().timestamp() > expires_at:
            flash('Срок действия кода истек. Запросите новый код', 'error')
            session.pop('sms_code', None)
            session.pop('sms_code_expires', None)
            return redirect(url_for('public.register'))
        
        # Проверка кода
        if code != expected_code:
            # Увеличиваем счетчик попыток (можно реализовать более детально)
            flash('Неверный код подтверждения', 'error')
            return render_template('public/verify_sms.html', code=code)
        
        # Код верный - завершаем регистрацию или вход
        if purpose == 'registration':
            reg_data = session.get('registration_data')
            
            # Генерация кода скидки
            discount_code = CodeGenerator.generate_discount_code(reg_data['store_code'])
            
            # Создание пользователя с паролем
            user = User(
                discount_code=discount_code,
                phone=reg_data['phone'],
                email=reg_data['email'],
                fio=reg_data.get('fio'),
                store_code=reg_data['store_code'],
                consent_pd=reg_data['consent_pd'],
                consent_pd_date=datetime.utcnow() if reg_data['consent_pd'] else None,
                consent_pd_version='1.0',  # Версия из настроек
                consent_marketing=reg_data.get('consent_marketing', False)
            )
            # Установка пароля
            user.set_password(reg_data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            # Отправка приветственного SMS
            sms_service = current_app.extensions.get('sms_service')
            if sms_service and current_app.config.get('SEND_WELCOME_SMS', True):
                discount_percent = current_app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)
                sms_service.send_welcome_sms(user.phone, user.discount_code, discount_percent)
            
            # Очистка сессии
            session.pop('registration_data', None)
            session.pop('sms_code', None)
            session.pop('sms_code_expires', None)
            session.pop('sms_purpose', None)
            
            # Сохраняем ID пользователя в сессии
            session['user_id'] = user.id
            
            flash('Регистрация успешна! Добро пожаловать в программу лояльности.', 'success')
            return redirect(url_for('dashboard.index'))
        
        elif purpose == 'login':
            login_identifier = session.get('login_identifier')  # Может быть phone или email
            # Поиск пользователя по телефону или email
            user = User.query.filter(
                (User.phone == login_identifier) | (User.email == login_identifier)
            ).first()
            
            if user and user.status == UserStatus.ACTIVE:
                # Обновляем дату последнего входа
                user.last_login_at = datetime.utcnow()
                db.session.commit()
                
                # Очистка сессии
                session.pop('login_identifier', None)
                session.pop('sms_code', None)
                session.pop('sms_code_expires', None)
                session.pop('sms_purpose', None)
                
                # Сохраняем ID пользователя в сессии
                session['user_id'] = user.id
                
                flash('Вход выполнен успешно', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Ошибка входа. Возможно, аккаунт заблокирован', 'error')
                return redirect(url_for('public.login'))
    
    return render_template('public/verify_sms.html')


@public_bp.route('/resend-sms', methods=['POST'])
def resend_sms():
    """Повторная отправка SMS-кода"""
    # Проверка задержки между отправками
    last_sent = session.get('sms_last_sent', 0)
    now = datetime.utcnow().timestamp()
    
    if now - last_sent < 60:
        remaining = int(60 - (now - last_sent))
        return {'success': False, 'message': f'Повторная отправка доступна через {remaining} сек.'}, 429
    
    # Генерация нового кода
    sms_code = CodeGenerator.generate_sms_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    purpose = session.get('sms_purpose', 'registration')
    
    session['sms_code'] = sms_code
    session['sms_code_expires'] = expires_at.timestamp()
    session['sms_last_sent'] = now
    
    # Отправка SMS
    if purpose == 'registration':
        phone = session.get('registration_data', {}).get('phone')
    else:
        phone = session.get('login_phone')
        # Для совместимости с новой логикой login_identifier
        if not phone:
            phone = session.get('login_identifier')
    
    if phone:
        sms_service = current_app.extensions.get('sms_service')
        if sms_service:
            sms_service.send_verification_code(phone, sms_code, purpose)
    
    return {'success': True, 'message': 'Код отправлен повторно'}


@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        login_input = request.form.get('login', '').strip()  # Может быть телефон или email
        
        if not login_input:
            flash('Введите e-mail или номер телефона', 'error')
            return render_template('public/login.html', login=login_input)
        
        # Пробуем определить тип ввода: телефон или email
        is_phone = login_input.startswith('+') or login_input[0].isdigit()
        
        if is_phone:
            # Валидация телефона
            is_valid, result = ValidationService.validate_phone(login_input)
            if not is_valid:
                flash(result, 'error')
                return render_template('public/login.html', login=login_input)
            normalized_login = result
        else:
            # Валидация email
            is_valid, result = ValidationService.validate_email(login_input)
            if not is_valid:
                flash(result, 'error')
                return render_template('public/login.html', login=login_input)
            normalized_login = result.lower()
        
        # Проверка существования пользователя по телефону или email
        user = User.query.filter(
            (User.phone == normalized_login) | (User.email == normalized_login)
        ).first()
        
        if not user:
            flash('Пользователь не найден. Пожалуйста, зарегистрируйтесь.', 'info')
            return redirect(url_for('public.register'))
        
        # Проверка статуса
        if user.status != UserStatus.ACTIVE:
            flash('Аккаунт заблокирован или согласие отозвано', 'error')
            return render_template('public/login.html', login=normalized_login)
        
        # Генерация SMS-кода для входа
        sms_code = CodeGenerator.generate_sms_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        session['login_identifier'] = normalized_login  # Сохраняем как телефон или email
        session['login_phone'] = user.phone  # Для обратной совместимости
        session['sms_code'] = sms_code
        session['sms_code_expires'] = expires_at.timestamp()
        session['sms_purpose'] = 'login'
        
        # Отправка SMS на телефон пользователя
        sms_service = current_app.extensions.get('sms_service')
        if sms_service:
            sms_service.send_verification_code(user.phone, sms_code, 'login')
        
        flash('Код подтверждения отправлен на ваш телефон', 'success')
        return redirect(url_for('public.verify_sms'))
    
    return render_template('public/login.html')


@public_bp.route('/logout')
def logout():
    """Выход из личного кабинета"""
    session.pop('user_id', None)
    flash('Вы вышли из личного кабинета', 'info')
    return redirect(url_for('public.index'))


@public_bp.route('/policy')
def policy():
    """Страница политики обработки персональных данных"""
    page = PageContent.get_active_page('pd_policy')
    if not page:
        page = PageContent(
            page_key='pd_policy',
            title='Политика обработки персональных данных',
            content='<p>Текст политики будет предоставлен заказчиком.</p>',
            version='1.0'
        )
    return render_template('public/policy.html', page=page)


@public_bp.route('/rules')
def rules():
    """Страница правил программы лояльности"""
    page = PageContent.get_active_page('loyalty_rules')
    if not page:
        page = PageContent(
            page_key='loyalty_rules',
            title='Правила программы лояльности',
            content='<p>Текст правил будет предоставлен заказчиком.</p>',
            version='1.0'
        )
    return render_template('public/rules.html', page=page)
