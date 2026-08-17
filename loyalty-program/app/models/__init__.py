import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import enum

db = SQLAlchemy()


class UserStatus(enum.Enum):
    """Статусы пользователя"""
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    REVOKED = 'revoked'  # Согласие отозвано


class User(db.Model):
    """Модель пользователя (покупателя)"""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    discount_code = Column(String(10), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(120), nullable=False)
    fio = Column(String(100), nullable=True)
    store_code = Column(String(3), nullable=False)  # Код магазина регистрации
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    # Согласия
    consent_pd = Column(Boolean, default=False, nullable=False)
    consent_pd_date = Column(DateTime, nullable=True)
    consent_pd_version = Column(String(20), nullable=True)
    consent_marketing = Column(Boolean, default=False, nullable=False)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Экспорт
    is_exported = Column(Boolean, default=False, nullable=False)
    exported_at = Column(DateTime, nullable=True)
    
    # Связи
    sms_codes = relationship('SMSCode', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    export_logs = relationship('ExportLogEntry', backref='user', lazy='dynamic')
    
    @validates('phone')
    def validate_phone(self, key, phone):
        """Валидация номера телефона"""
        if not phone.startswith('+7') or len(phone) != 12:
            raise ValueError('Неверный формат телефона. Ожидается +7XXXXXXXXXX')
        return phone
    
    @validates('discount_code')
    def validate_discount_code(self, key, code):
        """Валидация кода скидки"""
        if len(code) != 10 or not code.isdigit():
            raise ValueError('Код скидки должен быть 10-значным числом')
        return code
    
    def is_active_user(self):
        """Требуется Flask-Login"""
        return self.status == UserStatus.ACTIVE
    
    def to_dict(self):
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'discount_code': self.discount_code,
            'phone': self.phone,
            'email': self.email,
            'fio': self.fio,
            'store_code': self.store_code,
            'status': self.status.value,
            'consent_pd': self.consent_pd,
            'consent_pd_date': self.consent_pd_date.isoformat() if self.consent_pd_date else None,
            'consent_pd_version': self.consent_pd_version,
            'consent_marketing': self.consent_marketing,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_exported': self.is_exported,
            'exported_at': self.exported_at.isoformat() if self.exported_at else None
        }
    
    def __repr__(self):
        return f'<User {self.phone}>'


class SMSCode(db.Model):
    """Модель SMS-кода подтверждения"""
    
    __tablename__ = 'sms_codes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(String(4), nullable=False)
    phone = Column(String(20), nullable=False)
    purpose = Column(String(20), nullable=False)  # 'registration' или 'login'
    is_used = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    @validates('code')
    def validate_code(self, key, code):
        """Валидация кода"""
        if len(code) != 4 or not code.isdigit():
            raise ValueError('Код должен быть 4-значным числом')
        return code
    
    def is_valid(self):
        """Проверка валидности кода"""
        now = datetime.utcnow()
        return (
            not self.is_used and
            not self.is_expired and
            self.expires_at > now and
            self.attempts < 5
        )
    
    def __repr__(self):
        return f'<SMSCode {self.code} for {self.phone}>'


class AdminUser(UserMixin, db.Model):
    """Модель администратора"""
    
    __tablename__ = 'admin_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    def check_password(self, password):
        """Проверка пароля"""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_account_locked(self):
        """Проверка блокировки аккаунта"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False
    
    def record_failed_attempt(self, lockout_duration_minutes):
        """Запись неудачной попытки входа"""
        from datetime import timedelta
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_duration_minutes)
        db.session.commit()
    
    def reset_failed_attempts(self):
        """Сброс счетчика неудачных попыток"""
        self.failed_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'


class Setting(db.Model):
    """Модель настроек приложения"""
    
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(50), nullable=True)
    
    @classmethod
    def get_value(cls, key, default=None):
        """Получение значения настройки"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_value(cls, key, value, description=None, updated_by=None):
        """Установка значения настройки"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_by = updated_by
        else:
            setting = cls(key=key, value=value, description=description, updated_by=updated_by)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<Setting {self.key}>'


class ExportLog(db.Model):
    """Журнал экспортов данных"""
    
    __tablename__ = 'export_logs'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_format = Column(String(10), nullable=False)  # 'xlsx' или 'csv'
    record_count = Column(Integer, nullable=False)
    filters = Column(Text, nullable=True)  # JSON с фильтрами
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(50), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    
    # Связь с пользователями, попавшими в экспорт
    users = relationship('ExportLogEntry', backref='export_log', lazy='dynamic')
    
    def __repr__(self):
        return f'<ExportLog {self.filename}>'


class ExportLogEntry(db.Model):
    """Записи в журнале экспорта (связь пользователь-экспорт)"""
    
    __tablename__ = 'export_log_entries'
    
    id = Column(Integer, primary_key=True)
    export_log_id = Column(Integer, ForeignKey('export_logs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('export_log_id', 'user_id', name='unique_export_user'),
    )
    
    def __repr__(self):
        return f'<ExportLogEntry export={self.export_log_id} user={self.user_id}>'


class PageContent(db.Model):
    """Модель для редактируемых страниц (политика ПДн, правила)"""
    
    __tablename__ = 'page_contents'
    
    id = Column(Integer, primary_key=True)
    page_key = Column(String(50), unique=True, nullable=False)  # 'pd_policy', 'loyalty_rules'
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @classmethod
    def get_active_page(cls, page_key):
        """Получение активной версии страницы"""
        return cls.query.filter_by(page_key=page_key, is_active=True).first()
    
    def __repr__(self):
        return f'<PageContent {self.page_key} v{self.version}>'


class Purchase(db.Model):
    """Модель покупки (чека) покупателя"""
    
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    receipt_number = Column(String(50), nullable=False, index=True)  # Номер чека
    store_code = Column(String(3), nullable=False)  # Код магазина
    total_amount = Column(Integer, nullable=False)  # Сумма чека в копейках
    discount_amount = Column(Integer, default=0, nullable=False)  # Сумма скидки в копейках
    purchase_date = Column(DateTime, nullable=False, index=True)  # Дата покупки
    
    # Дополнительные данные (JSON)
    items = Column(Text, nullable=True)  # JSON со списком товаров (хранится как строка)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связь с пользователем
    user = relationship('User', backref=db.backref('purchases', lazy='dynamic'))
    
    def set_items(self, items_list):
        """Установка списка товаров (конвертирует в JSON строку)"""
        import json
        if items_list is None:
            self.items = None
        else:
            self.items = json.dumps(items_list, ensure_ascii=False)
    
    def get_items(self):
        """Получение списка товаров (парсит JSON строку)"""
        import json
        if not self.items:
            return []
        try:
            return json.loads(self.items)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def to_dict(self):
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'receipt_number': self.receipt_number,
            'store_code': self.store_code,
            'total_amount': self.total_amount,
            'discount_amount': self.discount_amount,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'items': self.get_items(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Purchase {self.receipt_number} user={self.user_id}>'
