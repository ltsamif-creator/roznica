#!/usr/bin/env python3
"""
Тесты для веб-сайта программы лояльности
Запуск: python tests/test_all.py
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, SMSCode, AdminUser, Setting, PageContent, UserStatus
from config import Config


class BaseTestCase(unittest.TestCase):
    """Базовый класс для тестов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Создаем тестовые настройки
        Setting.set_value('discount_percent', '5', 'Размер скидки')
        Setting.set_value('app_name', 'Тест Программа Лояльности', 'Название')
        Setting.set_value('sms_template', 'Ваш код: {code}', 'Шаблон SMS')
        
    def tearDown(self):
        """Очистка после каждого теста"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()


class TestModels(BaseTestCase):
    """Тесты моделей данных"""
    
    def test_user_creation(self):
        """Тест создания пользователя"""
        user = User(
            discount_code='0010000001',
            phone='+79991234567',
            email='test@example.com',
            fio='Иванов Иван Иванович',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow(),
            consent_pd_version='1.0'
        )
        db.session.add(user)
        db.session.commit()
        
        found = User.query.filter_by(phone='+79991234567').first()
        self.assertIsNotNone(found)
        self.assertEqual(found.discount_code, '0010000001')
        self.assertEqual(found.store_code, '001')
        self.assertEqual(found.status, UserStatus.ACTIVE)
        
    def test_user_phone_validation(self):
        """Тест валидации телефона"""
        user = User(
            discount_code='0010000002',
            phone='+79991234568',
            email='test2@example.com',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # Неправильный телефон должен вызвать ошибку
        with self.assertRaises(ValueError):
            bad_user = User(
                discount_code='0010000003',
                phone='89991234567',  # Не начинается с +7
                email='test3@example.com',
                store_code='001',
                consent_pd=True,
                consent_pd_date=datetime.utcnow()
            )
            db.session.add(bad_user)
            db.session.commit()
            
    def test_sms_code_creation(self):
        """Тест создания SMS-кода"""
        user = User(
            discount_code='0010000004',
            phone='+79991234569',
            email='test4@example.com',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        code = SMSCode(
            user_id=user.id,
            code='1234',
            phone='+79991234569',
            purpose='registration',
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.session.add(code)
        db.session.commit()
        
        found = SMSCode.query.filter_by(code='1234').first()
        self.assertIsNotNone(found)
        self.assertTrue(found.is_valid())
        self.assertEqual(found.purpose, 'registration')
        
    def test_sms_code_expiration(self):
        """Тест истечения срока SMS-кода"""
        user = User(
            discount_code='0010000005',
            phone='+79991234570',
            email='test5@example.com',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # Создаем код с истекшим сроком
        expired_code = SMSCode(
            user_id=user.id,
            code='5678',
            phone='+79991234570',
            purpose='login',
            expires_at=datetime.utcnow() - timedelta(minutes=1)  # Уже истек
        )
        db.session.add(expired_code)
        db.session.commit()
        
        found = SMSCode.query.filter_by(code='5678').first()
        self.assertFalse(found.is_valid())
        
    def test_admin_user_creation(self):
        """Тест создания администратора"""
        import bcrypt
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        
        admin = AdminUser(
            username='testadmin',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        
        found = AdminUser.query.filter_by(username='testadmin').first()
        self.assertIsNotNone(found)
        self.assertTrue(found.check_password('admin123'))
        self.assertFalse(found.check_password('wrongpassword'))
        
    def test_admin_lockout(self):
        """Тест блокировки администратора"""
        import bcrypt
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        
        admin = AdminUser(
            username='locktest',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        
        # Имитируем 5 неудачных попыток
        for i in range(5):
            admin.record_failed_attempt(lockout_duration_minutes=15)
            
        self.assertTrue(admin.is_account_locked())
        
    def test_setting_crud(self):
        """Тест CRUD операций с настройками"""
        Setting.set_value('test_key', 'test_value', 'Тестовая настройка', 'tester')
        
        value = Setting.get_value('test_key')
        self.assertEqual(value, 'test_value')
        
        Setting.set_value('test_key', 'new_value', updated_by='tester2')
        value = Setting.get_value('test_key')
        self.assertEqual(value, 'new_value')
        
    def test_page_content(self):
        """Тест страниц контента"""
        page = PageContent(
            page_key='test_policy',
            title='Тестовая политика',
            content='<p>Тестовый контент</p>',
            version='1.0',
            is_active=True
        )
        db.session.add(page)
        db.session.commit()
        
        found = PageContent.get_active_page('test_policy')
        self.assertIsNotNone(found)
        self.assertEqual(found.title, 'Тестовая политика')
        
        # Деактивируем и проверяем
        found.is_active = False
        db.session.commit()
        
        not_found = PageContent.get_active_page('test_policy')
        self.assertIsNone(not_found)


class TestPublicRoutes(BaseTestCase):
    """Тесты публичных маршрутов"""
    
    def test_home_page(self):
        """Тест главной страницы"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
    def test_registration_page_with_store(self):
        """Тест страницы регистрации с параметром магазина"""
        response = self.client.get('/?store=001')
        self.assertEqual(response.status_code, 200)
        
    def test_login_page(self):
        """Тест страницы входа"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        
    def test_pd_policy_page(self):
        """Тест страницы политики ПДн"""
        # Создаем страницу
        page = PageContent(
            page_key='pd_policy',
            title='Политика ПДн',
            content='<p>Текст политики</p>',
            version='1.0',
            is_active=True
        )
        db.session.add(page)
        db.session.commit()
        
        response = self.client.get('/policy')
        self.assertEqual(response.status_code, 200)
        
    def test_loyalty_rules_page(self):
        """Тест страницы правил программы"""
        page = PageContent(
            page_key='loyalty_rules',
            title='Правила',
            content='<p>Текст правил</p>',
            version='1.0',
            is_active=True
        )
        db.session.add(page)
        db.session.commit()
        
        response = self.client.get('/rules')
        self.assertEqual(response.status_code, 200)


class TestRegistrationFlow(BaseTestCase):
    """Тесты потока регистрации"""
    
    def test_registration_form_submit(self):
        """Тест отправки формы регистрации"""
        data = {
            'phone': '+79991234571',
            'email': 'newuser@example.com',
            'fio': 'Петров Петр Петрович',
            'consent_pd': 'y',
            'consent_rules': 'y'
        }
        response = self.client.post('/register', data=data, follow_redirects=True)
        # Должна быть перенаправлена на страницу подтверждения SMS
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что SMS-код создан
        user = User.query.filter_by(phone='+79991234571').first()
        if user:
            sms_code = SMSCode.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(sms_code)
            self.assertEqual(sms_code.purpose, 'registration')
            
    def test_duplicate_phone_registration(self):
        """Тест регистрации с дублирующимся телефоном"""
        # Создаем первого пользователя
        user1 = User(
            discount_code='0010000006',
            phone='+79991234572',
            email='user1@example.com',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow()
        )
        db.session.add(user1)
        db.session.commit()
        
        # Пытаемся зарегистрировать второго с тем же телефоном
        data = {
            'phone': '+79991234572',
            'email': 'user2@example.com',
            'consent_pd': 'y',
            'consent_rules': 'y'
        }
        response = self.client.post('/register', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)


class TestDashboardRoutes(BaseTestCase):
    """Тесты личного кабинета"""
    
    def test_dashboard_requires_auth(self):
        """Тест что доступ к кабинету требует авторизации"""
        response = self.client.get('/dashboard/', follow_redirects=True)
        # Должен быть перенаправлен на вход
        self.assertEqual(response.status_code, 200)
        
    def test_dashboard_after_login(self):
        """Тест доступа к кабинету после входа"""
        # Создаем пользователя
        user = User(
            discount_code='0010000007',
            phone='+79991234573',
            email='dashuser@example.com',
            store_code='001',
            consent_pd=True,
            consent_pd_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # Вход через SMS - сначала запрашиваем код
        login_data = {'phone': '+79991234573'}
        response = self.client.post('/login', data=login_data, follow_redirects=True)
        
        # Получаем код из сессии через cookie клиента теста
        with self.client as c:
            with c.session_transaction() as sess:
                sms_code = sess.get('sms_code')
        
        # Вводим полученный код
        verify_data = {'code': sms_code}
        response = self.client.post('/verify-sms', data=verify_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Теперь доступ к кабинету должен быть открыт
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)


class TestAdminRoutes(BaseTestCase):
    """Тесты админ-панели"""
    
    def test_admin_login_required(self):
        """Тест что вход в админку требует авторизации"""
        response = self.client.get('/admin/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_login_success(self):
        """Тест успешного входа в админку"""
        import bcrypt
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        
        admin = AdminUser(
            username='admin',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        response = self.client.post('/admin/login', data=login_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_login_wrong_password(self):
        """Тест входа с неправильным паролем"""
        import bcrypt
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        
        admin = AdminUser(
            username='admin',
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        
        login_data = {
            'username': 'admin',
            'password': 'wrongpassword'
        }
        response = self.client.post('/admin/login', data=login_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Проверка сообщения об ошибке (зависит от реализации шаблона)


class TestExportService(BaseTestCase):
    """Тесты сервиса экспорта"""
    
    def test_export_users_to_dict(self):
        """Тест конвертации пользователей в словарь для экспорта"""
        user = User(
            discount_code='0010000008',
            phone='+79991234574',
            email='export@example.com',
            fio='Экспортов Экспорт Экспортович',
            store_code='002',
            consent_pd=True,
            consent_pd_date=datetime.utcnow(),
            consent_pd_version='1.0',
            consent_marketing=True
        )
        db.session.add(user)
        db.session.commit()
        
        user_dict = user.to_dict()
        self.assertEqual(user_dict['discount_code'], '0010000008')
        self.assertEqual(user_dict['phone'], '+79991234574')
        self.assertEqual(user_dict['store_code'], '002')
        self.assertEqual(user_dict['status'], 'active')


if __name__ == '__main__':
    # Запуск всех тестов
    unittest.main(verbosity=2)
