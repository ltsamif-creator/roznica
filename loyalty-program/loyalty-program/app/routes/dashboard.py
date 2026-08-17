from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from datetime import datetime, timedelta
from functools import wraps
import io
import json
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
from ..models import db, User, UserStatus, Setting, ExportLog, PageContent, Purchase
from ..services.export import ExportService

dashboard_bp = Blueprint('dashboard', __name__)


def login_required(f):
    """Декоратор для защиты страниц личного кабинета"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в личный кабинет', 'warning')
            return redirect(url_for('public.login'))
        
        # Проверяем существование пользователя
        user = User.query.get(session['user_id'])
        if not user or user.status != UserStatus.ACTIVE:
            session.pop('user_id', None)
            flash('Сессия недействительна. Пожалуйста, войдите снова', 'error')
            return redirect(url_for('public.login'))
        
        return f(*args, **kwargs)
    return decorated_function


@dashboard_bp.route('/')
@login_required
def index():
    """Главная страница личного кабинета"""
    user = User.query.get(session['user_id'])
    
    # Получаем размер скидки из настроек
    discount_percent = Setting.get_value('discount_percent', 
                                         str(current_app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)))
    
    return render_template('dashboard/index.html', 
                         user=user, 
                         discount_percent=discount_percent)


@dashboard_bp.route('/show-code')
@login_required
def show_code():
    """Экран показа кода скидки на весь экран"""
    user = User.query.get(session['user_id'])
    
    discount_percent = Setting.get_value('discount_percent',
                                         str(current_app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)))
    app_name = Setting.get_value('app_name', 
                                 current_app.config.get('APP_NAME', 'Программа Лояльности'))
    
    return render_template('dashboard/show_code.html', 
                         user=user,
                         discount_percent=discount_percent,
                         app_name=app_name)


@dashboard_bp.route('/barcode.png')
@login_required
def get_barcode():
    """Генерация штрих-кода для карты лояльности"""
    user = User.query.get(session['user_id'])
    
    # Создаем штрих-код Code128 с номером карты
    barcode = Code128(user.discount_code, writer=ImageWriter())
    
    # Генерируем изображение в буфер
    buffer = io.BytesIO()
    barcode.write(buffer, options={'module_width': 0.4, 'module_height': 15.0, 'font_size': 10})
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=False,
        download_name=f'barcode_{user.discount_code}.png'
    )


@dashboard_bp.route('/revoke-consent', methods=['GET', 'POST'])
@login_required
def revoke_consent():
    """Отзыв согласия на обработку персональных данных"""
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Помечаем пользователя как отозвавшего согласие
        user.status = UserStatus.REVOKED
        db.session.commit()
        
        # Очищаем сессию
        session.pop('user_id', None)
        
        flash('Ваше согласие на обработку персональных данных отозвано. Код скидки деактивирован.', 'info')
        return redirect(url_for('public.index'))
    
    return render_template('dashboard/revoke_consent.html', user=user)


@dashboard_bp.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    user = User.query.get(session['user_id'])
    
    return render_template('dashboard/profile.html', user=user)


@dashboard_bp.route('/api/user-info')
@login_required
def api_user_info():
    """API: Информация о пользователе"""
    user = User.query.get(session['user_id'])
    return {'success': True, 'user': user.to_dict()}


@dashboard_bp.route('/purchases')
@login_required
def purchases():
    """Страница истории покупок пользователя"""
    user = User.query.get(session['user_id'])
    
    # Получаем покупки пользователя, сортируем по дате (новые сверху)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = user.purchases.order_by(Purchase.purchase_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Подсчитываем общую сумму скидок
    total_discount = db.session.query(db.func.sum(Purchase.discount_amount)).filter(
        Purchase.user_id == user.id
    ).scalar() or 0
    
    # Подсчитываем общую сумму покупок
    total_spent = db.session.query(db.func.sum(Purchase.total_amount)).filter(
        Purchase.user_id == user.id
    ).scalar() or 0
    
    return render_template('dashboard/purchases.html', 
                         user=user,
                         pagination=pagination,
                         total_discount=total_discount,
                         total_spent=total_spent)


@dashboard_bp.route('/api/purchases')
@login_required
def api_purchases():
    """API: Список покупок пользователя"""
    user = User.query.get(session['user_id'])
    
    # Получаем все покупки
    purchases = user.purchases.order_by(Purchase.purchase_date.desc()).all()
    
    return {
        'success': True,
        'purchases': [p.to_dict() for p in purchases],
        'total_count': len(purchases)
    }
