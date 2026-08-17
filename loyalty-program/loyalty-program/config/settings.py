import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовая конфигурация приложения"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_APP = os.environ.get('FLASK_APP', 'app/__init__.py')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///loyalty.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Admin
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')
    
    # SMS Gateway
    SMS_API_URL = os.environ.get('SMS_API_URL', '')
    SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
    SMS_SENDER = os.environ.get('SMS_SENDER', 'LoyaltyProgram')
    
    # Application Settings
    APP_NAME = os.environ.get('APP_NAME', 'Программа Лояльности')
    DEFAULT_DISCOUNT_PERCENT = int(os.environ.get('DEFAULT_DISCOUNT_PERCENT', '5'))
    CODE_LENGTH = int(os.environ.get('CODE_LENGTH', '10'))
    STORE_CODE_LENGTH = int(os.environ.get('STORE_CODE_LENGTH', '3'))
    
    # Security
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', '8'))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', '15'))
    SMS_CODE_LENGTH = int(os.environ.get('SMS_CODE_LENGTH', '4'))
    SMS_CODE_EXPIRY_MINUTES = int(os.environ.get('SMS_CODE_EXPIRY_MINUTES', '5'))
    MAX_SMS_ATTEMPTS = int(os.environ.get('MAX_SMS_ATTEMPTS', '5'))
    SMS_RETRY_DELAY_SECONDS = int(os.environ.get('SMS_RETRY_DELAY_SECONDS', '60'))
    
    # Export
    EXPORT_RETENTION_DAYS = int(os.environ.get('EXPORT_RETENTION_DAYS', '30'))
    CSV_DELIMITER = os.environ.get('CSV_DELIMITER', ';')
    CSV_ENCODING = os.environ.get('CSV_ENCODING', 'utf-8-sig')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXPORT_DIR = os.path.join(BASE_DIR, 'data', 'exports')
    
    @classmethod
    def init_app(cls, app):
        """Инициализация приложения"""
        pass


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        # В продакшене создаем директорию для экспортов
        os.makedirs(cls.EXPORT_DIR, exist_ok=True)


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
