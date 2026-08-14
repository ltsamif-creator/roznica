"""
Loyalty Program - Веб-сайт программы лояльности
Flask application factory
"""

import os
from flask import Flask, session
from datetime import timedelta

from config import config, Config
from app.models import db, AdminUser, Setting, PageContent, UserStatus


def create_app(config_name=None):
    """Factory function для создания приложения Flask"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Загрузка конфигурации
    app.config.from_object(config[config_name])
    Config.init_app(app)
    
    # Явно устанавливаем URI базы данных из конфига
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('DATABASE_URL', 'sqlite:///loyalty.db')
    
    # Инициализация расширений
    db.init_app(app)
    
    # Регистрация сервисов
    from app.services import SMSService
    sms_service = SMSService()
    sms_service.init_app(app)
    app.extensions['sms_service'] = sms_service
    
    # Регистрация blueprint'ов
    from app.routes.public import public_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(admin_bp)
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    # Контекстные процессоры
    @app.context_processor
    def inject_globals():
        """Добавление глобальных переменных в контекст шаблонов"""
        return {
            'app_name': app.config.get('APP_NAME', 'Программа Лояльности'),
            'discount_percent': app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)
        }
    
    # Настройка сессии
    @app.before_request
    def make_session_permanent():
        """Делаем сессию постоянной с таймаутом"""
        session.permanent = True
        app.permanent_session_lifetime = timedelta(
            hours=app.config.get('SESSION_TIMEOUT_HOURS', 8)
        )
    
    return app


def register_error_handlers(app):
    """Регистрация обработчиков ошибок"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template_with_context(app, 'errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template_with_context(app, 'errors/500.html'), 500


def render_template_with_context(app, template_name, **kwargs):
    """Вспомогательная функция для рендеринга шаблонов в обработчиках ошибок"""
    from flask import render_template
    
    # Добавляем стандартные переменные контекста
    kwargs['app_name'] = app.config.get('APP_NAME', 'Программа Лояльности')
    kwargs['discount_percent'] = app.config.get('DEFAULT_DISCOUNT_PERCENT', 5)
    
    return render_template(template_name, **kwargs)


# Импорт моделей должен быть после создания db
from app.models import User, SMSCode, AdminUser, Setting, ExportLog, PageContent
