import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import datetime
from bot.db import get_rents_ending_today, get_pool, get_debts_due_today, get_debts_due_tomorrow, get_overdue_debts
from typing import TYPE_CHECKING
from bot.agenda import send_agenda, get_admins, send_reminder
from bot.logger_config import setup_logging, log_user_action, log_error
from bot.constants import ERROR_MESSAGES
import pytz

# Загрузка переменных окружения
load_dotenv("config/.env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMINS_FILE = "config/admins.txt"

# Проверка обязательных переменных окружения
if not TELEGRAM_TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не найден в переменных окружения")
    sys.exit(1)

# Чтение списка Telegram ID админов
try:
    with open(ADMINS_FILE, "r", encoding='utf-8') as f:
        ADMINS = set(line.strip() for line in f if line.strip())
    if not ADMINS:
        print("❌ Ошибка: Список админов пуст")
        sys.exit(1)
except FileNotFoundError:
    print(f"❌ Ошибка: Файл {ADMINS_FILE} не найден")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка при чтении файла админов: {e}")
    sys.exit(1)

# Настройка логирования
logger = setup_logging()

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

from bot import handlers
dp.include_router(handlers.router)

# Проверка: является ли пользователь админом
async def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMINS

@dp.message(CommandStart())
async def handle_start(message: Message):
    if await is_admin(message.from_user.id):
        await message.answer("👋 Привет, администратор! Добро пожаловать в XRent Bot.\nИспользуйте меню для управления ПК и арендой.")
    else:
        await message.answer("⛔️ У вас нет доступа. Только для администраторов.")

def get_admins():
    return ADMINS

async def send_agenda(bot: 'Bot', admins):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rents = await get_rents_ending_today()
    if not rents:
        text = "🗓️ Адженда на сегодня\n\nНет устройств с истекающей арендой."
        for admin_id in admins:
            await bot.send_message(admin_id, text)
        return
    text = "🗓️ Адженда на сегодня\n\nПК, аренда которых заканчивается сегодня:\n"
    for i, r in enumerate(rents, 1):
        end_date = r['start_date'] + datetime.timedelta(days=r['days']-1)
        phone = r.get('client_phone') or '—'
        telegram = r.get('client_telegram') or '—'
        text += f"\n{i}. 💻 {r['device_serial_number']} ({r['type']})\n   Клиент: {r['client_name']}\n   Адрес: {r['client_address']}\n   Телефон арендатора: {phone}\n   Telegram арендатора: {telegram}\n   Сумма: {int(r['rent_amount'])}₽\n   До: {end_date.strftime('%d.%m.%Y')}\n"
    for admin_id in admins:
        await bot.send_message(admin_id, text)
        for r in rents:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Завершить аренду", callback_data=f"finishrent_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="🔄 Продлить аренду", callback_data=f"prolong_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"device_{r['device_serial_number']}")]
            ])
            end_date = r['start_date'] + datetime.timedelta(days=r['days']-1)
            phone = r.get('client_phone') or '—'
            telegram = r.get('client_telegram') or '—'
            msg = (
                f"💻 {r['device_serial_number']} ({r['type']})\n"
                f"Клиент: {r['client_name']}\n"
                f"Адрес: {r['client_address']}\n"
                f"Телефон арендатора: {phone}\n"
                f"Telegram арендатора: {telegram}\n"
                f"Сумма: {int(r['rent_amount'])}₽\n"
                f"Аренда до: {end_date.strftime('%d.%m.%Y')}"
            )
            await bot.send_message(admin_id, msg, reply_markup=kb)

async def agenda_task(bot):
    while True:
        now = datetime.datetime.now()
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            await send_agenda(bot, get_admins())
        except Exception as e:
            logging.error(f"Agenda send error: {e}")
        await asyncio.sleep(60)

async def reminder_task(bot):
    moscow_tz = pytz.timezone('Europe/Moscow')
    while True:
        now = datetime.datetime.now(moscow_tz)
        next_run = now.replace(hour=11, minute=00, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            await send_reminder(bot, get_admins(), days_ahead=3)
        except Exception as e:
            logging.error(f"Reminder send error: {e}")
        await asyncio.sleep(60)

async def debt_reminder_task(bot):
    moscow_tz = pytz.timezone('Europe/Moscow')
    while True:
        now = datetime.datetime.now(moscow_tz)
        next_run = now.replace(hour=17, minute=44, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            admins = get_admins()
            overdue = await get_overdue_debts()
            today = await get_debts_due_today()
            tomorrow = await get_debts_due_tomorrow()
            text = "💸 <b>Напоминание о должниках</b>\n\n"
            def format_date(val):
                if val is None:
                    return "—"
                if isinstance(val, str):
                    try:
                        return datetime.datetime.strptime(val, "%Y-%m-%d").strftime('%d.%m.%Y')
                    except Exception:
                        return val
                if isinstance(val, datetime.date):
                    return val.strftime('%d.%m.%Y')
                return str(val)
            if overdue:
                text += "<b>❗️ Просрочено:</b>\n"
                for r in overdue:
                    text += f"• 💻 {r['device_serial_number']} ({r['type']}) — 👤 {r['client_name']}, {int(r['rent_amount'])}₽, до {format_date(r['expected_payment_date'])}\n"
            if today:
                text += "\n<b>⏰ Оплата сегодня:</b>\n"
                for r in today:
                    text += f"• 💻 {r['device_serial_number']} ({r['type']}) — 👤 {r['client_name']}, {int(r['rent_amount'])}₽, до {format_date(r['expected_payment_date'])}\n"
            if tomorrow:
                text += "\n<b>🕑 Оплата завтра:</b>\n"
                for r in tomorrow:
                    text += f"• 💻 {r['device_serial_number']} ({r['type']}) — 👤 {r['client_name']}, {int(r['rent_amount'])}₽, до {format_date(r['expected_payment_date'])}\n"
            if not (overdue or today or tomorrow):
                text += "Нет должников! 🎉"
            for admin_id in admins:
                await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Debt reminder send error: {e}")
        await asyncio.sleep(60)

async def main():
    asyncio.create_task(agenda_task(bot))
    asyncio.create_task(reminder_task(bot))
    asyncio.create_task(debt_reminder_task(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 