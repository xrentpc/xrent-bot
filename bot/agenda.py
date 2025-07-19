"""
Модуль для формирования и отправки ежедневной адженды администраторам.
"""
import datetime
from bot.db import get_overdue_rents, get_device_stats, get_month_revenue, get_rents_ending_soon, get_nominal_revenue, get_real_revenue
import os
from dotenv import load_dotenv

load_dotenv("config/.env")
ADMINS_FILE = "config/admins.txt"
with open(ADMINS_FILE, "r") as f:
    ADMINS = set(line.strip() for line in f if line.strip())

def get_admins():
    return ADMINS

async def send_agenda(bot, admins):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    stats = await get_device_stats()
    nominal = await get_nominal_revenue()
    real = await get_real_revenue()
    revenue = int(nominal)
    real_revenue = int(real)
    rents = await get_overdue_rents()
    text = (
        f"📊 Статистика:\n"
        f"В аренде: {stats['in_rent']}  🟠\n"
        f"В ремонте: {stats['in_repair']}  🛠️\n"
        f"Свободно: {stats['free']}  🟢\n"
        f"💰 Номинальная выручка: {revenue}₽\n"
        f"💵 Реальная выручка: {real_revenue}₽\n\n"
        f"🗓️ Адженда на сегодня\n\n"
    )
    if not rents:
        text += "Нет устройств с истекшей или истекающей арендой."
        for admin_id in admins:
            await bot.send_message(admin_id, text)
        return
    text += "ПК, аренда которых истекла или истекает сегодня:"
    for admin_id in admins:
        await bot.send_message(admin_id, text)
        for r in rents:
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
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Завершить аренду", callback_data=f"finishrent_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="🔄 Продлить аренду", callback_data=f"prolong_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"device_{r['device_serial_number']}")]
            ])
            await bot.send_message(admin_id, msg, reply_markup=kb)

async def send_reminder(bot, admins, days_ahead: int = 3):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    stats = await get_device_stats()
    nominal = await get_nominal_revenue()
    real = await get_real_revenue()
    revenue = int(nominal)
    real_revenue = int(real)
    soon_rents = await get_rents_ending_soon(days_ahead)
    text = (
        f"📊 Статистика:\n"
        f"В аренде: {stats['in_rent']}  🟠\n"
        f"В ремонте: {stats['in_repair']}  🛠️\n"
        f"Свободно: {stats['free']}  🟢\n"
        f"💰 Номинальная выручка: {revenue}₽\n"
        f"💵 Реальная выручка: {real_revenue}₽\n\n"
        f"⏰ Напоминание! В ближайшие {days_ahead} дня(ей) завершатся следующие аренды:\n"
    )
    if not soon_rents:
        text += "Нет аренд, завершающихся в ближайшие дни."
        for admin_id in admins:
            await bot.send_message(admin_id, text)
        return
    for admin_id in admins:
        await bot.send_message(admin_id, text)
        for i, r in enumerate(soon_rents, 1):
            end_date = r['start_date'] + datetime.timedelta(days=r['days']-1)
            phone = r.get('client_phone') or '—'
            telegram = r.get('client_telegram') or '—'
            msg = (
                f"{i}. 💻 {r['device_serial_number']} ({r['type']})\n"
                f"Клиент: {r['client_name']}\n"
                f"Адрес: {r['client_address']}\n"
                f"Телефон арендатора: {phone}\n"
                f"Telegram арендатора: {telegram}\n"
                f"Сумма: {int(r['rent_amount'])}₽\n"
                f"До: {end_date.strftime('%d.%m.%Y')}\n"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Завершить аренду", callback_data=f"finishrent_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="🔄 Продлить аренду", callback_data=f"prolong_{r['device_serial_number']}")],
                [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"device_{r['device_serial_number']}")]
            ])
            await bot.send_message(admin_id, msg, reply_markup=kb) 