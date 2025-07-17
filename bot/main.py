import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import datetime
from bot.db import get_rents_ending_today, get_pool
from typing import TYPE_CHECKING
from bot.agenda import send_agenda, get_admins, send_reminder
import pytz

# Загрузка переменных окружения
load_dotenv("config/.env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMINS_FILE = "config/admins.txt"

# Чтение списка Telegram ID админов
with open(ADMINS_FILE, "r") as f:
    ADMINS = set(line.strip() for line in f if line.strip())

# Логирование
logging.basicConfig(level=logging.INFO)

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

async def main():
    asyncio.create_task(agenda_task(bot))
    asyncio.create_task(reminder_task(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 