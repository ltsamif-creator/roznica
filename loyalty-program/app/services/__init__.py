import secrets
import string
from datetime import datetime, timedelta
import sys
import os

# Добавляем родительский путь для импорта моделей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import db, User, SMSCode


class CodeGenerator:
    """Генератор уникальных кодов скидки"""
    
    @staticmethod
    def generate_discount_code(store_code: str) -> str:
        """
        Генерация 10-значного кода скидки
        
        Args:
            store_code: 3-значный код магазина (001-013)
            
        Returns:
            10-значный код скидки
        """
        if len(store_code) != 3 or not store_code.isdigit():
            raise ValueError('Код магазина должен быть 3-значным числом')
        
        max_attempts = 100
        for _ in range(max_attempts):
            # Генерируем 7 случайных цифр для порядкового номера
            # Используем криптографически стойкий генератор
            sequential_part = ''.join(secrets.choice(string.digits) for _ in range(7))
            discount_code = f"{store_code}{sequential_part}"
            
            # Проверяем уникальность
            existing = User.query.filter_by(discount_code=discount_code).first()
            if not existing:
                return discount_code
        
        raise Exception('Не удалось сгенерировать уникальный код после 100 попыток')
    
    @staticmethod
    def generate_sms_code() -> str:
        """
        Генерация 4-значного SMS-кода подтверждения
        
        Returns:
            4-значный код
        """
        return ''.join(secrets.choice(string.digits) for _ in range(4))


class SMSService:
    """Сервис отправки SMS (заглушка для разработки)"""
    
    def __init__(self, app=None):
        self.app = app
        self.sent_messages = []  # Для тестирования
    
    def init_app(self, app):
        self.app = app
    
    def send_verification_code(self, phone: str, code: str, purpose: str = 'registration') -> bool:
        """
        Отправка SMS с кодом подтверждения
        
        Args:
            phone: Номер телефона в формате +7XXXXXXXXXX
            code: 4-значный код подтверждения
            purpose: Назначение ('registration' или 'login')
            
        Returns:
            True если успешно, False иначе
        """
        if self.app:
            config = self.app.config
            sms_text = config.get('SMS_VERIFICATION_TEMPLATE', 
                                  'Ваш код подтверждения: {code}. Действует 5 минут.')
            sms_text = sms_text.format(code=code)
        else:
            sms_text = f'Ваш код подтверждения: {code}. Действует 5 минут.'
        
        # В продакшене здесь будет вызов API SMS-шлюза
        # Для разработки просто логируем сообщение
        self.sent_messages.append({
            'phone': phone,
            'code': code,
            'purpose': purpose,
            'text': sms_text,
            'sent_at': datetime.utcnow()
        })
        
        # Логирование для отладки
        print(f"[SMS] {phone}: {sms_text}")
        
        # Всегда возвращаем True в режиме разработки
        return True
    
    def send_welcome_sms(self, phone: str, discount_code: str, discount_percent: int) -> bool:
        """
        Отправка приветственного SMS с кодом скидки
        
        Args:
            phone: Номер телефона
            discount_code: Код скидки покупателя
            discount_percent: Размер скидки в процентах
            
        Returns:
            True если успешно
        """
        sms_text = f"Добро пожаловать в программу лояльности! Ваша скидка {discount_percent}%. Код: {discount_code}. Показывайте код кассиру."
        
        self.sent_messages.append({
            'phone': phone,
            'text': sms_text,
            'type': 'welcome',
            'sent_at': datetime.utcnow()
        })
        
        print(f"[SMS Welcome] {phone}: {sms_text}")
        return True
    
    def get_last_sent_code(self, phone: str) -> str | None:
        """Получение последнего отправленного кода для телефона (для тестов)"""
        for msg in reversed(self.sent_messages):
            if msg.get('phone') == phone and 'code' in msg:
                return msg['code']
        return None


class ValidationService:
    """Сервис валидации данных"""
    
    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, str]:
        """
        Валидация номера телефона (упрощенная)
        
        Args:
            phone: Номер телефона
            
        Returns:
            (is_valid, normalized_phone или сообщение об ошибке)
        """
        # Временное логирование для отладки
        print(f"[DEBUG] Получен номер телефона: {repr(phone)}")
        
        if not phone:
            return False, 'Номер телефона обязателен'
        
        # Удаляем все нецифровые символы
        clean_phone = ''.join(c for c in phone if c.isdigit())
        
        print(f"[DEBUG] Очищенный номер: {clean_phone}")
        
        # Проверяем длину и начало номера
        if len(clean_phone) != 11:
            return False, 'Номер должен содержать 11 цифр'
        
        if not (clean_phone.startswith('7') or clean_phone.startswith('8')):
            return False, 'Номер должен начинаться с 7 или 8'
        
        # Приводим к формату +7XXXXXXXXXX
        if clean_phone.startswith('8'):
            clean_phone = '7' + clean_phone[1:]
        
        normalized = '+' + clean_phone
        
        print(f"[DEBUG] Нормализованный номер: {normalized}")
        
        return True, normalized
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """
        Валидация e-mail
        
        Returns:
            (is_valid, message)
        """
        from email_validator import validate_email, EmailNotValidError
        
        if not email:
            return False, 'E-mail обязателен'
        
        try:
            valid = validate_email(email)
            return True, valid.email
        except EmailNotValidError as e:
            return False, str(e)
    
    @staticmethod
    def validate_fio(fio: str) -> tuple[bool, str]:
        """
        Валидация ФИО
        
        Returns:
            (is_valid, message)
        """
        if not fio:
            return True, ''  # ФИО необязательно
        
        if len(fio) > 100:
            return False, 'ФИО не должно превышать 100 символов'
        
        # Базовая проверка на допустимые символы
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюяABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ -')
        if not all(c in allowed_chars for c in fio):
            return False, 'ФИО содержит недопустимые символы'
        
        return True, fio.strip()


class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self):
        self.requests = {}  # {ip: [(timestamp, endpoint), ...]}
    
    def is_allowed(self, ip: str, endpoint: str = 'default', 
                   max_requests: int = 5, window_seconds: int = 900) -> bool:
        """
        Проверка, разрешен ли запрос
        
        Args:
            ip: IP-адрес клиента
            endpoint: Тип эндпоинта
            max_requests: Максимум запросов за окно времени
            window_seconds: Размер окна в секундах (по умолчанию 15 минут)
            
        Returns:
            True если запрос разрешен
        """
        now = datetime.utcnow().timestamp()
        key = f"{ip}:{endpoint}"
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Очищаем старые записи
        self.requests[key] = [
            ts for ts in self.requests[key]
            if now - ts < window_seconds
        ]
        
        # Проверяем лимит
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Добавляем текущий запрос
        self.requests[key].append(now)
        return True
    
    def get_retry_after(self, ip: str, endpoint: str = 'default', 
                        window_seconds: int = 900) -> int:
        """Получение времени до сброса лимита в секундах"""
        key = f"{ip}:{endpoint}"
        if key not in self.requests or not self.requests[key]:
            return 0
        
        oldest = min(self.requests[key])
        retry_after = int(window_seconds - (datetime.utcnow().timestamp() - oldest))
        return max(0, retry_after)
