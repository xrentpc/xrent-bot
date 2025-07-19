"""
Утилиты для XRent Bot
"""

import re
import logging
from datetime import datetime
from typing import Optional, Union
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from .constants import ERROR_MESSAGES, PHONE_REGEX, DATE_REGEX

logger = logging.getLogger(__name__)

def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    return bool(re.fullmatch(PHONE_REGEX, phone.strip()))

def validate_date(date_str: str) -> Optional[datetime]:
    """Валидация даты в формате ДД.ММ.ГГГГ"""
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except (ValueError, TypeError):
        return None

def validate_days(days_str: str) -> Optional[int]:
    """Валидация количества дней"""
    try:
        days = int(days_str)
        return days if days > 0 else None
    except (ValueError, TypeError):
        return None

def validate_sum(sum_str: str) -> Optional[float]:
    """Валидация суммы"""
    try:
        sum_val = float(sum_str.replace(",", "."))
        return sum_val if sum_val > 0 else None
    except (ValueError, TypeError, AttributeError):
        return None

def validate_discount(discount_str: str) -> Optional[float]:
    """Валидация процента скидки"""
    try:
        discount = float(discount_str.replace(",", "."))
        return discount if 0 <= discount <= 100 else None
    except (ValueError, TypeError, AttributeError):
        return None

def sanitize_input(text: str, max_length: int = 500) -> str:
    """Санитизация пользовательского ввода"""
    if not text:
        return ""
    # Удаляем потенциально опасные символы
    sanitized = re.sub(r'[<>"\']', '', text.strip())
    # Ограничиваем длину
    return sanitized[:max_length]

def format_currency(amount: Union[int, float]) -> str:
    """Форматирование валюты"""
    return f"{int(amount)}₽"

def format_date(date_obj: datetime) -> str:
    """Форматирование даты"""
    return date_obj.strftime('%d.%m.%Y')

def safe_message_edit(message_or_cb: Union[Message, CallbackQuery], text: str, **kwargs):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        if isinstance(message_or_cb, Message):
            return message_or_cb.answer(text, **kwargs)
        else:
            return message_or_cb.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            if not isinstance(message_or_cb, Message):
                message_or_cb.answer("Уже выбран этот фильтр")
        else:
            logger.error(f"Error editing message: {e}")
            raise

async def handle_database_error(func, *args, **kwargs):
    """Обработчик ошибок базы данных"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Database error in {func.__name__}: {e}")
        raise

def log_user_action(user_id: int, action: str, details: str = ""):
    """Логирование действий пользователя"""
    logger.info(f"User {user_id} performed action: {action} {details}")



def get_error_message(error_type: str) -> str:
    """Получение сообщения об ошибке"""
    return ERROR_MESSAGES.get(error_type, "Произошла ошибка")

def is_cancellation_message(text: str) -> bool:
    """Проверка на сообщение отмены"""
    return text == "❌ Отмена"

def extract_serial_from_text(text: str) -> Optional[str]:
    """Извлечение серийного номера из текста"""
    # Ищем паттерн серийного номера (например, X001, PC001)
    match = re.search(r'[A-Z]+\d+', text)
    return match.group() if match else None 