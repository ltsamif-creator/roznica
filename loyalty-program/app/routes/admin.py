from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
import json
from ..models import db, User, AdminUser, Setting, ExportLog, PageContent, UserStatus
from ..services.export import ExportService
from ..services import ValidationService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Сервис экспорта
export_service = ExportService()


def admin_login_required(f):
    """Декоратор для защиты админ-панели"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin.login'))
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.is_active:
            session.pop('admin_id', None)
            return redirect(url_for('admin.login'))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в админ-панель"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if not admin:
            flash('Неверный логин или пароль', 'error')
            return render_template('admin/login.html')
        
        # Проверка блокировки
        if admin.is_account_locked():
            flash('Аккаунт заблокирован. Попробуйте позже', 'error')
            return render_template('admin/login.html')
        
        # Проверка пароля
        if not admin.check_password(password):
            admin.record_failed_attempt(current_app.config.get('LOCKOUT_DURATION_MINUTES', 15))
            flash('Неверный логин или пароль', 'error')
            return render_template('admin/login.html')
        
        # Успешный вход
        admin.reset_failed_attempts()
        admin.last_login_at = datetime.utcnow()
        db.session.commit()
        
        session['admin_id'] = admin.id
        
        flash('Вход выполнен успешно', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Выход из админ-панели"""
    session.pop('admin_id', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_login_required
def dashboard():
    """Дашборд администратора"""
    # Статистика
    total_users = User.query.count()
    today_users = User.query.filter(
        User.created_at >= datetime.utcnow().date()
    ).count()
    week_users = User.query.filter(
        User.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Пользователи по магазинам
    stores_stats = db.session.query(
        User.store_code, 
        db.func.count(User.id)
    ).group_by(User.store_code).all()
    
    # График регистраций (последние 7 дней)
    registration_stats = []
    for i in range(6, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        count = User.query.filter(
            User.created_at >= date,
            User.created_at < date + timedelta(days=1)
        ).count()
        registration_stats.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         today_users=today_users,
                         week_users=week_users,
                         stores_stats=stores_stats,
                         registration_stats=registration_stats)


@admin_bp.route('/users')
@admin_login_required
def users():
    """Список пользователей"""
    # Параметры фильтрации
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    status_filter = request.args.get('status', '')
    store_filter = request.args.get('store', '')
    search = request.args.get('search', '')
    only_new = request.args.get('only_new', '') == '1'
    
    # Построение запроса
    query = User.query
    
    if status_filter:
        query = query.filter(User.status == status_filter)
    
    if store_filter:
        query = query.filter(User.store_code == store_filter)
    
    if only_new:
        query = query.filter(User.is_exported == False)
    
    if search:
        query = query.filter(
            db.or_(
                User.phone.contains(search),
                User.email.contains(search),
                User.discount_code.contains(search),
                User.fio.contains(search) if User.fio is not None else False
            )
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Получаем список магазинов для фильтра
    stores = db.session.query(User.store_code).distinct().all()
    
    return render_template('admin/users.html',
                         pagination=pagination,
                         stores=stores,
                         filters={
                             'status': status_filter,
                             'store': store_filter,
                             'search': search,
                             'only_new': only_new
                         })


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_login_required
def toggle_user_status(user_id):
    """Блокировка/разблокировка пользователя"""
    user = User.query.get_or_404(user_id)
    
    if user.status == UserStatus.ACTIVE:
        user.status = UserStatus.BLOCKED
        flash(f'Пользователь {user.phone} заблокирован', 'info')
    else:
        user.status = UserStatus.ACTIVE
        flash(f'Пользователь {user.phone} разблокирован', 'success')
    
    db.session.commit()
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/export', methods=['GET', 'POST'])
@admin_login_required
def export():
    """Экспорт данных"""
    if request.method == 'POST':
        # Получаем параметры
        only_new = request.form.get('only_new') == 'on'
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')
        store_code = request.form.get('store_code')
        file_format = request.form.get('file_format', 'xlsx')
        
        # Парсинг дат
        date_from_dt = None
        date_to_dt = None
        
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                flash('Неверный формат даты от', 'error')
                return redirect(url_for('admin.export'))
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                flash('Неверный формат даты до', 'error')
                return redirect(url_for('admin.export'))
        
        # Получаем пользователей
        users = export_service.get_users_for_export(
            only_new=only_new,
            date_from=date_from_dt,
            date_to=date_to_dt,
            store_code=store_code if store_code else None
        )
        
        if not users:
            flash('Нет данных для экспорта по указанным фильтрам', 'warning')
            return redirect(url_for('admin.export'))
        
        # Выполняем экспорт
        admin = AdminUser.query.get(session['admin_id'])
        filters = {
            'only_new': only_new,
            'date_from': date_from,
            'date_to': date_to,
            'store_code': store_code
        }
        
        result = export_service.perform_export(
            users=users,
            file_format=file_format,
            created_by=admin.username,
            filters=filters
        )
        
        if result:
            # Отправляем файл на скачивание
            filename = result['filename']
            content = result['content']
            
            if file_format.lower() == 'csv':
                return send_file(
                    io.BytesIO(content.encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                return send_file(
                    io.BytesIO(content),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=filename
                )
    
    # GET запрос - показываем форму
    export_history = export_service.get_export_history(limit=20)
    stores = db.session.query(User.store_code).distinct().all()
    
    return render_template('admin/export.html',
                         export_history=export_history,
                         stores=stores)


@admin_bp.route('/export/history')
@admin_login_required
def export_history():
    """История экспортов"""
    exports = export_service.get_export_history(limit=50)
    return render_template('admin/export_history.html', exports=exports)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_login_required
def settings():
    """Настройки приложения"""
    if request.method == 'POST':
        admin = AdminUser.query.get(session['admin_id'])
        
        # Сохраняем настройки
        settings_to_save = {
            'discount_percent': request.form.get('discount_percent', '5'),
            'app_name': request.form.get('app_name', 'Программа Лояльности'),
            'sms_template': request.form.get('sms_template', ''),
            'send_welcome_sms': '1' if request.form.get('send_welcome_sms') else '0'
        }
        
        for key, value in settings_to_save.items():
            Setting.set_value(key, value, updated_by=admin.username)
        
        flash('Настройки сохранены', 'success')
        return redirect(url_for('admin.settings'))
    
    # Загружаем текущие настройки
    current_settings = {
        'discount_percent': Setting.get_value('discount_percent', '5'),
        'app_name': Setting.get_value('app_name', 'Программа Лояльности'),
        'sms_template': Setting.get_value('sms_template', 'Ваш код подтверждения: {code}. Действует 5 минут.'),
        'send_welcome_sms': Setting.get_value('send_welcome_sms', '1') == '1'
    }
    
    return render_template('admin/settings.html', settings=current_settings)


@admin_bp.route('/pages/<page_key>', methods=['GET', 'POST'])
@admin_login_required
def edit_page(page_key):
    """Редактирование статических страниц"""
    valid_pages = ['pd_policy', 'loyalty_rules']
    if page_key not in valid_pages:
        flash('Страница не найдена', 'error')
        return redirect(url_for('admin.dashboard'))
    
    page = PageContent.get_active_page(page_key)
    
    if request.method == 'POST':
        admin = AdminUser.query.get(session['admin_id'])
        
        title = request.form.get('title', '')
        content = request.form.get('content', '')
        version = request.form.get('version', '1.0')
        
        if page:
            # Создаем новую версию, старую деактивируем
            page.is_active = False
            db.session.commit()
        
        new_page = PageContent(
            page_key=page_key,
            title=title,
            content=content,
            version=version,
            is_active=True
        )
        db.session.add(new_page)
        db.session.commit()
        
        flash('Страница обновлена', 'success')
        return redirect(url_for('admin.edit_page', page_key=page_key))
    
    return render_template('admin/edit_page.html', page=page, page_key=page_key)
