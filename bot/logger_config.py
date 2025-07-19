"""
Настройка логирования для XRent Bot
"""

import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging():
    """Настройка структурированного логирования"""
    
    # Создаем папку для логов если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'xrent_bot.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Отдельный файл для ошибок
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # Отдельный файл для действий пользователей
    user_actions_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'user_actions.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    user_actions_handler.setLevel(logging.INFO)
    user_actions_handler.setFormatter(formatter)
    
    # Создаем специальный логгер для действий пользователей
    user_logger = logging.getLogger('user_actions')
    user_logger.setLevel(logging.INFO)
    user_logger.addHandler(user_actions_handler)
    user_logger.propagate = False  # Не дублируем в основной лог
    
    # Настройка логгеров для внешних библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncpg').setLevel(logging.WARNING)
    
    return logger

def log_user_action(user_id: int, action: str, details: str = ""):
    """Логирование действий пользователя"""
    user_logger = logging.getLogger('user_actions')
    user_logger.info(f"USER_ACTION | User: {user_id} | Action: {action} | Details: {details}")

def log_database_operation(operation: str, table: str, details: str = ""):
    """Логирование операций с базой данных"""
    logger = logging.getLogger('database')
    logger.info(f"DB_OPERATION | Operation: {operation} | Table: {table} | Details: {details}")

def log_performance(operation: str, duration: float, details: str = ""):
    """Логирование производительности"""
    logger = logging.getLogger('performance')
    logger.info(f"PERFORMANCE | Operation: {operation} | Duration: {duration:.3f}s | Details: {details}")

def log_security_event(event_type: str, user_id: int, details: str = ""):
    """Логирование событий безопасности"""
    logger = logging.getLogger('security')
    logger.warning(f"SECURITY | Event: {event_type} | User: {user_id} | Details: {details}")

def log_error(error: Exception, context: str = ""):
    """Логирование ошибок"""
    logger = logging.getLogger('errors')
    logger.error(f"ERROR | Context: {context} | Error: {error}", exc_info=True) 