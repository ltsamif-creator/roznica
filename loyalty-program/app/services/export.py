import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import json
import os
import sys

# Добавляем родительский путь для импорта моделей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import db, User, ExportLog, ExportLogEntry


class ExportService:
    """Сервис экспорта данных пользователей"""
    
    def __init__(self, export_dir: str = None):
        self.export_dir = export_dir or 'data/exports'
        os.makedirs(self.export_dir, exist_ok=True)
    
    def get_users_for_export(self, only_new: bool = True, 
                             date_from: datetime = None,
                             date_to: datetime = None,
                             store_code: str = None) -> list[User]:
        """
        Получение списка пользователей для экспорта
        
        Args:
            only_new: Только не экспортированные ранее
            date_from: Дата от (по дате регистрации)
            date_to: Дата до
            store_code: Код магазина (опционально)
            
        Returns:
            Список пользователей
        """
        query = User.query
        
        if only_new:
            query = query.filter(User.is_exported == False)
        
        if date_from:
            query = query.filter(User.created_at >= date_from)
        
        if date_to:
            query = query.filter(User.created_at <= date_to)
        
        if store_code:
            query = query.filter(User.store_code == store_code)
        
        # Исключаем пользователей с отозванным согласием
        query = query.filter(User.status != 'revoked')
        
        return query.order_by(User.created_at).all()
    
    def generate_csv(self, users: list[User], delimiter: str = ';', 
                     encoding: str = 'utf-8-sig') -> tuple[str, str]:
        """
        Генерация CSV файла
        
        Args:
            users: Список пользователей
            delimiter: Разделитель полей
            encoding: Кодировка файла
            
        Returns:
            (filename, content) - имя файла и содержимое
        """
        data = []
        for user in users:
            data.append({
                'discount_code': user.discount_code,
                'phone': user.phone,
                'email': user.email,
                'fio': user.fio or '',
                'store_code': user.store_code,
                'reg_date': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'consent_pd': 1 if user.consent_pd else 0,
                'consent_pd_date': user.consent_pd_date.strftime('%Y-%m-%d %H:%M:%S') if user.consent_pd_date else '',
                'consent_pd_version': user.consent_pd_version or '',
                'consent_marketing': 1 if user.consent_marketing else 0,
                'status': user.status.value
            })
        
        df = pd.DataFrame(data)
        
        # Генерируем имя файла
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'loyalty_export_{timestamp}.csv'
        
        # Конвертируем в CSV
        csv_content = df.to_csv(
            sep=delimiter, 
            index=False, 
            encoding=encoding,
            line_terminator='\n'
        )
        
        return filename, csv_content
    
    def generate_xlsx(self, users: list[User]) -> tuple[str, bytes]:
        """
        Генерация XLSX файла
        
        Args:
            users: Список пользователей
            
        Returns:
            (filename, content) - имя файла и байты файла
        """
        data = []
        for user in users:
            data.append({
                'Код скидки': user.discount_code,
                'Телефон': user.phone,
                'E-mail': user.email,
                'ФИО': user.fio or '',
                'Магазин': user.store_code,
                'Дата регистрации': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Согласие ПДн': 'Да' if user.consent_pd else 'Нет',
                'Дата согласия ПДн': user.consent_pd_date.strftime('%Y-%m-%d %H:%M:%S') if user.consent_pd_date else '',
                'Версия согласия': user.consent_pd_version or '',
                'Согласие на рассылку': 'Да' if user.consent_marketing else 'Нет',
                'Статус': self._get_status_label(user.status.value)
            })
        
        df = pd.DataFrame(data)
        
        # Генерируем имя файла
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'loyalty_export_{timestamp}.xlsx'
        
        # Сохраняем в буфер
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Пользователи')
            
            # Форматирование
            worksheet = writer.sheets['Пользователи']
            
            # Автоширина колонок
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        return filename, buffer.getvalue()
    
    def _get_status_label(self, status_value: str) -> str:
        """Получение читаемого названия статуса"""
        labels = {
            'active': 'Активен',
            'blocked': 'Заблокирован',
            'revoked': 'Согласие отозвано'
        }
        return labels.get(status_value, status_value)
    
    def create_export_log(self, filename: str, file_format: str, 
                          record_count: int, filters: dict, 
                          created_by: str = None) -> ExportLog:
        """
        Создание записи в журнале экспортов
        
        Args:
            filename: Имя файла
            file_format: Формат ('csv' или 'xlsx')
            record_count: Количество записей
            filters: Фильтры экспорта (JSON)
            created_by: Пользователь, создавший экспорт
            
        Returns:
            Экземпляр ExportLog
        """
        export_log = ExportLog(
            filename=filename,
            file_format=file_format,
            record_count=record_count,
            filters=json.dumps(filters),
            created_by=created_by
        )
        db.session.add(export_log)
        db.session.commit()
        
        return export_log
    
    def mark_users_as_exported(self, users: list[User], export_log: ExportLog):
        """
        Пометка пользователей как экспортированных
        
        Args:
            users: Список пользователей
            export_log: Журнал экспорта
        """
        now = datetime.utcnow()
        
        for user in users:
            user.is_exported = True
            user.exported_at = now
            
            # Добавляем связь с экспортом
            entry = ExportLogEntry(
                export_log_id=export_log.id,
                user_id=user.id
            )
            db.session.add(entry)
        
        db.session.commit()
    
    def perform_export(self, users: list[User], file_format: str = 'xlsx',
                       created_by: str = None, filters: dict = None) -> dict:
        """
        Выполнение полного цикла экспорта
        
        Args:
            users: Список пользователей для экспорта
            file_format: Формат файла ('csv' или 'xlsx')
            created_by: Пользователь, инициировавший экспорт
            filters: Фильтры экспорта
            
        Returns:
            dict с информацией об экспорте:
            - filename: Имя файла
            - content: Содержимое файла (строка или байты)
            - format: Формат файла
            - record_count: Количество записей
            - export_id: ID записи в журнале
        """
        if not users:
            return None
        
        # Генерируем файл
        if file_format.lower() == 'csv':
            filename, content = self.generate_csv(users)
        else:
            filename, content = self.generate_xlsx(users)
        
        # Создаем запись в журнале
        export_log = self.create_export_log(
            filename=filename,
            file_format=file_format.lower(),
            record_count=len(users),
            filters=filters or {},
            created_by=created_by
        )
        
        # Помечаем пользователей как экспортированных
        self.mark_users_as_exported(users, export_log)
        
        return {
            'filename': filename,
            'content': content,
            'format': file_format.lower(),
            'record_count': len(users),
            'export_id': export_log.id
        }
    
    def get_export_history(self, limit: int = 50) -> list[ExportLog]:
        """
        Получение истории экспортов
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список записей журнала экспортов
        """
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        return ExportLog.query.filter(
            ExportLog.created_at >= cutoff_date
        ).order_by(
            ExportLog.created_at.desc()
        ).limit(limit).all()
    
    def increment_download_count(self, export_log_id: int):
        """Увеличение счетчика скачиваний"""
        export_log = ExportLog.query.get(export_log_id)
        if export_log:
            export_log.download_count += 1
            db.session.commit()
