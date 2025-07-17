# Здесь будут дополнительные хендлеры команд, меню и логики бота 

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
from bot.db import get_free_devices, get_base_rent, create_rent, get_device_info, get_rent_history, get_rent_history_count, get_repair_history, get_repair_history_count, get_rent_last_date, get_repair_last_date, create_repair, finish_repair, get_pool, add_device_comment, get_last_device_comment, get_device_comments
from aiogram.exceptions import TelegramBadRequest
from bot.agenda import send_agenda, get_admins, send_reminder
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router()

# Таблица коэффициентов (день: коэффициент)
RENT_COEFFICIENTS = {
    1: 1.0, 2: 0.9, 3: 0.8, 4: 0.775, 5: 0.75, 6: 0.725, 7: 0.7, 8: 0.6913, 9: 0.6826, 10: 0.6729,
    11: 0.6652, 12: 0.6565, 13: 0.6487, 14: 0.6391, 15: 0.6304, 16: 0.6217, 17: 0.613, 18: 0.6043,
    19: 0.5957, 20: 0.587, 21: 0.5783, 22: 0.5696, 23: 0.5609, 24: 0.5522, 25: 0.5435, 26: 0.5348,
    27: 0.5261, 28: 0.5174, 29: 0.5087, 30: 0.5
}

DEVICE_STATUS = [
    ("all", "Все"),
    ("Свободен", "🟢 Свободен"),
    ("В аренде", "🔴 В аренде"),
    ("На ремонте", "🛠️ На ремонте")
]

class RentStates(StatesGroup):
    choosing_device = State()
    entering_fio = State()
    entering_address = State()
    entering_date = State()
    entering_days = State()
    entering_sum = State()
    entering_discount = State()
    entering_phone = State()
    entering_telegram = State()
    confirming = State()

class RepairStates(StatesGroup):
    entering_comment = State()
    confirming = State()
    entering_finish_comment = State()
    confirming_finish = State()

class CommentStates(StatesGroup):
    entering_comment = State()

class FinishRentStates(StatesGroup):
    confirming = State()

class AddDeviceStates(StatesGroup):
    entering_serial = State()
    entering_type = State()
    entering_date = State()
    entering_price = State()
    entering_base_rent = State()
    confirming = State()

class DeleteDeviceStates(StatesGroup):
    choosing = State()
    confirming = State()

# Старт оформления аренды
@router.message(Command("rent"))
async def start_rent(message: Message, state: FSMContext):
    devices = await get_free_devices()
    if not devices:
        await message.answer("❗️ Нет доступных ПК для аренды.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"💻 {d['serial_number']} ({d['type']})")] for d in devices] + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await message.answer("📝 Выберите ПК для аренды:", reply_markup=kb)
    await state.set_state(RentStates.choosing_device)
    await state.update_data(devices=devices)

@router.message(RentStates.choosing_device)
async def choose_device(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    data = await state.get_data()
    devices = data.get("devices", [])
    selected = next((d for d in devices if message.text.startswith(f"💻 {d['serial_number']}")), None)
    if not selected:
        await message.answer("⚠️ Пожалуйста, выберите ПК из списка или нажмите 'Отмена'.")
        return
    await state.update_data(selected_device=selected)
    await message.answer("👤 Введите ФИО клиента:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_fio)

@router.message(RentStates.entering_fio)
async def enter_fio(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(client_fio=message.text)
    await message.answer("🏠 Введите адрес клиента:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_address)

@router.message(RentStates.entering_address)
async def enter_address(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(client_address=message.text)
    await message.answer("📅 Введите дату начала аренды (ДД.ММ.ГГГГ):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_date)

@router.message(RentStates.entering_date)
async def enter_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if not message.text:
        await message.answer("❗️ Введите дату в формате ДД.ММ.ГГГГ.")
        return
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        await message.answer("❗️ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ.")
        return
    await state.update_data(start_date=start_date)
    await message.answer("🔢 Введите количество дней аренды:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_days)

@router.message(RentStates.entering_days)
async def enter_days(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if not message.text:
        await message.answer("❗️ Введите корректное число дней.")
        return
    try:
        days = int(message.text)
        if days <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❗️ Введите корректное число дней.")
        return
    await state.update_data(days=days)
    data = await state.get_data()
    device = data.get("selected_device", {})
    serial_number = device.get("serial_number")
    prolong_start_date = data.get("prolong_start_date")
    if prolong_start_date:
        start_date = prolong_start_date
    else:
        start_date = data.get("start_date")
    if not start_date:
        await message.answer("Ошибка: не удалось определить дату начала аренды.")
        await state.clear()
        return
    if days <= 30:
        base_rent = await get_base_rent(serial_number)
        if base_rent is None:
            await message.answer("❗️ Не удалось получить стоимость аренды для выбранного ПК.")
            await state.clear()
            return
        coeff = RENT_COEFFICIENTS.get(days, 1.0)
        rent_sum = round(base_rent * days * coeff, 2)
        await state.update_data(rent_sum=rent_sum, coeff=coeff, start_date=start_date)
        end_date = start_date + timedelta(days=days-1)
        await message.answer(f"Продление: с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')} ({days} дней)")
        await confirm_rent(message, state)
    else:
        await message.answer("💸 Введите сумму аренды вручную:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(RentStates.entering_sum)

@router.message(RentStates.entering_sum)
async def enter_sum(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if not message.text:
        await message.answer("❗️ Введите корректную сумму.")
        return
    try:
        rent_sum = float(message.text.replace(",", "."))
        if rent_sum <= 0:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        await message.answer("❗️ Введите корректную сумму.")
        return
    await state.update_data(rent_sum=rent_sum, coeff=None)
    data = await state.get_data()
    start_date = data.get("start_date")
    if not start_date:
        prolong_start_date = data.get("prolong_start_date")
        if prolong_start_date:
            await state.update_data(start_date=prolong_start_date)
        else:
            await message.answer("Ошибка: не удалось определить дату начала аренды.")
            await state.clear()
            return
    await confirm_rent(message, state)

async def confirm_rent(message: Message, state: FSMContext):
    data = await state.get_data()
    device = data.get("selected_device", {})
    fio = data.get("client_fio")
    address = data.get("client_address")
    start_date = data.get("start_date")
    days = data.get("days")
    rent_sum = data.get("rent_sum")
    coeff = data.get("coeff")
    # Новый шаг: запрос скидки
    await message.answer(
        f"💸 Сумма аренды: {rent_sum}₽\n"
        f"Хотите применить скидку? Введите процент (например, 10) или 0, если не нужно.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="0")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(RentStates.entering_discount)

@router.message(RentStates.entering_discount)
async def enter_discount(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if not message.text:
        await message.answer("❗️ Введите корректный процент скидки от 0 до 100.")
        return
    try:
        discount = float(message.text.replace(",", "."))
        if discount < 0 or discount > 100:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        await message.answer("❗️ Введите корректный процент скидки от 0 до 100.")
        return
    data = await state.get_data()
    rent_sum = data.get("rent_sum") or 0.0
    rent_sum_discounted = round(rent_sum * (1 - discount / 100), 2)
    await state.update_data(discount_percent=discount, rent_sum_discounted=rent_sum_discounted)
    # Если это продление, сразу к подтверждению
    if data.get("prolong_start_date"):
        # Используем старые телефон и Telegram
        device = data.get("selected_device", {})
        fio = data.get("client_fio") or "—"
        address = data.get("client_address") or "—"
        start_date = data.get("prolong_start_date")
        days = data.get("days") or 1
        coeff = data.get("coeff") or 1.0
        discount = discount
        rent_sum_discounted = rent_sum_discounted
        phone = data.get("client_phone") or "—"
        telegram = data.get("client_telegram") or "—"
        if start_date is not None:
            start_date_str = start_date.strftime('%d.%m.%Y')
        else:
            start_date_str = "—"
        text = (
            f"✅ Проверьте данные продления:\n"
            f"ПК: 💻 {device.get('serial_number')} ({device.get('type')})\n"
            f"Клиент: 👤 {fio}\n"
            f"Адрес: 🏠 {address}\n"
            f"Телефон арендатора: {phone}\n"
            f"Telegram арендатора: {telegram}\n"
            f"Дата начала: 📅 {start_date_str}\n"
            f"Дней: 🔢 {days}\n"
            f"Коэффициент: {coeff if coeff is not None else 'индивидуально'}\n"
            f"Скидка: {discount}%\n"
            f"Сумма: 💸 {rent_sum_discounted}₽"
        )
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Подтвердить")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
        await message.answer(text, reply_markup=kb)
        await state.set_state(RentStates.confirming)
        return
    # Если не продление — обычный сценарий
    await message.answer("📞 Введите номер телефона клиента (например, +79991234567):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_phone)

@router.message(RentStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    phone = message.text.strip()
    # Простая валидация: начинается с +7 или 8, 11-12 цифр
    import re
    if not re.fullmatch(r"(\+7|8)\d{10}", phone):
        await message.answer("❗️ Введите корректный номер телефона в формате +79991234567 или 89991234567.")
        return
    await state.update_data(client_phone=phone)
    await message.answer("@ Введите Telegram-тег клиента (например, @username) или пропустите, отправив -", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="-")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_telegram)

@router.message(RentStates.entering_telegram)
async def enter_telegram(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    telegram_tag = message.text.strip()
    if telegram_tag == "-":
        telegram_tag = ""
    elif not telegram_tag.startswith("@") or len(telegram_tag) < 2:
        await message.answer("❗️ Введите корректный Telegram-тег (например, @username) или отправьте - для пропуска.")
        return
    await state.update_data(client_telegram=telegram_tag)
    # Переходим к подтверждению
    data = await state.get_data()
    device = data.get("selected_device", {})
    fio = data.get("client_fio") or "—"
    address = data.get("client_address") or "—"
    start_date = data.get("start_date")
    days = data.get("days") or 1
    coeff = data.get("coeff") or 1.0
    discount = data.get("discount_percent") or 0.0
    rent_sum_discounted = data.get("rent_sum_discounted") or 0.0
    phone = data.get("client_phone") or ""
    telegram = telegram_tag or "—"
    if start_date is not None:
        start_date_str = start_date.strftime('%d.%m.%Y')
    else:
        start_date_str = "—"
    text = (
        f"✅ Проверьте данные аренды:\n"
        f"ПК: 💻 {device.get('serial_number')} ({device.get('type')})\n"
        f"Клиент: 👤 {fio}\n"
        f"Адрес: 🏠 {address}\n"
        f"Телефон: 📞 {phone}\n"
        f"Telegram: {telegram}\n"
        f"Дата начала: 📅 {start_date_str}\n"
        f"Дней: 🔢 {days}\n"
        f"Коэффициент: {coeff if coeff is not None else 'индивидуально'}\n"
        f"Скидка: {discount}%\n"
        f"Сумма: 💸 {rent_sum_discounted}₽"
    )
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Подтвердить")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await message.answer(text, reply_markup=kb)
    await state.set_state(RentStates.confirming)

@router.message(RentStates.confirming)
async def finish_rent(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить":
        data = await state.get_data()
        device = data.get("selected_device", {})
        rent_id = data.get("rent_id")
        if rent_id:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE rents SET status = 'завершена' WHERE id = $1", rent_id)
        client_fio = data.get("client_fio") or "—"
        client_address = data.get("client_address") or "—"
        start_date = data.get("start_date")
        days = data.get("days") or 1
        rent_sum_discounted = data.get("rent_sum_discounted") or 0.0
        coeff = data.get("coeff") or 1.0
        discount_percent = data.get("discount_percent") or 0.0
        client_phone = data.get("client_phone") or ""
        client_telegram = data.get("client_telegram") or ""
        await create_rent(
            device_serial_number=device.get("serial_number"),
            client_fio=client_fio,
            client_address=client_address,
            start_date=start_date,
            days=days,
            rent_amount=rent_sum_discounted,
            coefficient=coeff,
            discount_percent=discount_percent,
            client_phone=client_phone,
            client_telegram=client_telegram
        )
        start_date_str = start_date.strftime('%d.%m.%Y') if start_date else "—"
        await message.answer(
            f"🎉 Аренда оформлена!\n"
            f"ПК: 💻 {device.get('serial_number')}\n"
            f"Клиент: 👤 {client_fio}\n"
            f"С {start_date_str} на {days} дней.\n"
            f"Сумма: 💸 {rent_sum_discounted}₽",
            reply_markup=ReplyKeyboardRemove()
        )
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить' или 'Отмена'.")

@router.message(Command("devices"))
async def show_devices(message: Message):
    await show_devices_list(message, status_filter="all")

async def show_devices_list(message_or_cb, status_filter="all"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status_filter == "all":
            rows = await conn.fetch("SELECT serial_number, type, status FROM devices ORDER BY serial_number")
        else:
            rows = await conn.fetch("SELECT serial_number, type, status FROM devices WHERE status = $1 ORDER BY serial_number", status_filter)
    if not rows:
        await message_or_cb.answer("❗️ Нет устройств по выбранному фильтру.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{r['serial_number']} ({r['type']}) {status_emoji(r['status'])}", callback_data=f"device_{r['serial_number']}")] for r in rows
        ] + [
            [InlineKeyboardButton(text=label, callback_data=f"filter_{code}") for code, label in DEVICE_STATUS]
        ]
    )
    text = "🖥️ Список устройств:\nВыберите устройство для просмотра подробностей или используйте фильтр по статусу."
    try:
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=kb)
        else:
            await message_or_cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            if not isinstance(message_or_cb, Message):
                await message_or_cb.answer("Уже выбран этот фильтр")
        else:
            raise

def status_emoji(status):
    if status == "Свободен":
        return "🟢"
    if status == "В аренде":
        return "🔴"
    if status == "На ремонте":
        return "🛠️"
    return "❔"

@router.callback_query(F.data.startswith("filter_"))
async def filter_devices(cb: CallbackQuery):
    code = cb.data.replace("filter_", "")
    await show_devices_list(cb, status_filter=code)
    await cb.answer()

HISTORY_PAGE_SIZE = 5

@router.callback_query(F.data.startswith("device_"))
async def show_device_card(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("device_", "")
    info = await get_device_info(serial)
    if not info:
        await cb.answer("Устройство не найдено", show_alert=True)
        return
    profit_str = f"💰 {int(info['profit'])}₽" if info['profit'] >= 0 else f"🔻 {int(info['profit'])}₽"
    # Получаем активную аренду для даты окончания и клиента
    pool = await get_pool()
    async with pool.acquire() as conn:
        rent = await conn.fetchrow("SELECT start_date, days, client_name, client_phone, client_telegram FROM rents WHERE device_serial_number = $1 AND status = 'активна' ORDER BY start_date DESC LIMIT 1", serial)
    end_date_str = "—"
    client_phone = client_telegram = "—"
    if rent and rent["start_date"] and rent["days"]:
        end_date = rent["start_date"] + timedelta(days=rent["days"]-1)
        end_date_str = end_date.strftime('%d.%m.%Y')
        client_phone = rent["client_phone"] or "—"
        client_telegram = rent["client_telegram"] or "—"
    last_comment = await get_last_device_comment(serial)
    text = (
        f"💻 {info['serial_number']} ({info['type']})\n"
        f"Статус: {status_emoji(info['status'])} {info['status']}\n"
        f"Дата покупки: {info['purchase_date'].strftime('%d.%m.%Y')}\n"
        f"Сумма покупки: {int(info['purchase_amount'])}₽\n"
        f"Прибыль: {profit_str}\n"
        f"Комментарий: {last_comment or '-'}\n\n"
        f"В аренде: {info['total_rent_days']} дней\n"
        f"В ремонте: {info['total_repair_days']} дней\n"
        f"В простое: {info['total_idle_days']} дней\n"
        f"Аренда до: {end_date_str}\n"
        f"Телефон арендатора: {client_phone}\n"
        f"Telegram арендатора: {client_telegram}"
    )
    # Динамические кнопки
    buttons = []
    if info['status'] == 'Свободен':
        buttons.append([InlineKeyboardButton(text="📝 Оформить аренду", callback_data=f"rent_{serial}")])
    if info['status'] == 'В аренде':
        buttons.append([InlineKeyboardButton(text="🔄 Продлить аренду", callback_data=f"prolong_{serial}")])
        buttons.append([InlineKeyboardButton(text="✅ Завершить аренду", callback_data=f"finishrent_{serial}")])
    if info['status'] != 'На ремонте':
        buttons.append([InlineKeyboardButton(text="🛠️ Оформить ремонт", callback_data=f"repair_{serial}")])
    if info['status'] == 'На ремонте':
        buttons.append([InlineKeyboardButton(text="✅ Завершить ремонт", callback_data=f"finishrepair_{serial}")])
    # Всегда доступные кнопки
    buttons.append([InlineKeyboardButton(text="📜 История", callback_data=f"history_{serial}_0")])
    buttons.append([InlineKeyboardButton(text="➕ Комментарий", callback_data=f"comment_{serial}")])
    buttons.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="filter_all")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("history_"))
async def show_device_history(cb: CallbackQuery):
    # Формат callback_data: history_SERIAL_offset
    parts = cb.data.split("_")
    serial = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    offset = page * HISTORY_PAGE_SIZE
    # Получаем историю и статистику
    rent_count = await get_rent_history_count(serial)
    repair_count = await get_repair_history_count(serial)
    rent_last = await get_rent_last_date(serial)
    repair_last = await get_repair_last_date(serial)
    # Изменяем сортировку: самые новые аренды сверху
    rents = await get_rent_history(serial, offset=offset, limit=HISTORY_PAGE_SIZE, desc=True)
    pool = await get_pool()
    async with pool.acquire() as conn:
        repairs = await conn.fetch(
            "SELECT repair_date, problem_comment, solution_comment FROM repairs WHERE device_serial_number = $1 ORDER BY repair_date DESC OFFSET $2 LIMIT $3",
            serial, offset, HISTORY_PAGE_SIZE
        )
        rent_contacts = await conn.fetch(
            "SELECT start_date, client_phone, client_telegram FROM rents WHERE device_serial_number = $1 ORDER BY start_date DESC OFFSET $2 LIMIT $3",
            serial, offset, HISTORY_PAGE_SIZE
        )
        rent_contacts_map = {(r["start_date"],): (r["client_phone"], r["client_telegram"]) for r in rent_contacts}
    # Формируем текст
    text = f"📜 История устройства {serial}\n\n"
    text += f"Всего аренд: {rent_count}"
    if rent_last:
        text += f" | Последняя аренда: {rent_last.strftime('%d.%m.%Y')}"
    text += "\n"
    text += f"Всего ремонтов: {repair_count}"
    if repair_last:
        text += f" | Последний ремонт: {repair_last.strftime('%d.%m.%Y')}"
    text += "\n\n"
    if rents:
        text += "Аренды:\n"
        for i, r in enumerate(rents, start=1+offset):
            end_date = r['start_date'] + timedelta(days=r['days']-1) if r['start_date'] and r['days'] else None
            end_date_str = end_date.strftime('%d.%m.%Y') if end_date else "—"
            phone, tg = rent_contacts_map.get((r['start_date'],), ("—", "—"))
            text += f"{i}. {r['start_date'].strftime('%d.%m.%Y')} — {end_date_str} ({r['days']} дн.), {r['client_name']}, {int(r['rent_amount'])}₽, {r['status']}\n   Телефон: {phone} | Telegram: {tg}\n"
    else:
        text += "Аренды: нет\n"
    if repairs:
        text += "\nРемонты:\n"
        for i, r in enumerate(repairs, start=1+offset):
            date_str = r['repair_date'].strftime('%d.%m.%Y') if r['repair_date'] else "—"
            problem = r['problem_comment'] or "—"
            solution = r['solution_comment']
            if solution:
                text += f"{i}. {date_str} — {problem} — {solution}\n"
            else:
                text += f"{i}. {date_str} — {problem}\n"
    else:
        text += "\nРемонты: нет\n"
    comments = await get_device_comments(serial)
    if comments:
        text += "\nКомментарии:\n"
        for i, c in enumerate(comments, start=1):
            date_str = c["created_at"].strftime('%d.%m.%Y %H:%M') if c["created_at"] else "—"
            text += f"{i}. {date_str} — {c['comment']}\n"
    else:
        text += "\nКомментарии: нет\n"
    # Кнопки пагинации + возврат к карточке
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"history_{serial}_{page-1}"))
    if rent_count > offset + HISTORY_PAGE_SIZE or repair_count > offset + HISTORY_PAGE_SIZE:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"history_{serial}_{page+1}"))
    nav_buttons.append(InlineKeyboardButton(text="⬅️ К устройству", callback_data=f"device_{serial}"))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[nav_buttons]
    )
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("rent_"))
async def start_rent_from_card(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("rent_", "")
    # Получаем устройство из базы
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT serial_number, type FROM devices WHERE serial_number = $1 AND status = 'Свободен'", serial)
        if not row:
            await cb.answer("Устройство уже занято или не найдено", show_alert=True)
            return
        device = {"serial_number": row["serial_number"], "type": row["type"]}
    await state.update_data(devices=[device], selected_device=device)
    await cb.message.answer(f"📝 Оформление аренды для {device['serial_number']} ({device['type']})")
    await cb.message.answer("👤 Введите ФИО клиента:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_fio)
    await cb.answer()

@router.callback_query(F.data.startswith("prolong_"))
async def prolong_rent(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("prolong_", "")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rent = await conn.fetchrow("SELECT id, client_name, client_address, start_date, days, rent_amount, coefficient, client_phone, client_telegram FROM rents WHERE device_serial_number = $1 AND status = 'активна' ORDER BY start_date DESC LIMIT 1", serial)
        if not rent:
            await cb.answer("Активная аренда не найдена", show_alert=True)
            return
        device = await conn.fetchrow("SELECT serial_number, type FROM devices WHERE serial_number = $1", serial)
        if not device:
            await cb.answer("Устройство не найдено", show_alert=True)
            return
    start_date = rent["start_date"] + timedelta(days=rent["days"])
    await state.update_data(
        rent_id=rent["id"],
        selected_device={"serial_number": device["serial_number"], "type": device["type"]},
        client_fio=rent["client_name"],
        client_address=rent["client_address"],
        prolong_start_date=start_date,
        client_phone=rent["client_phone"] or "",
        client_telegram=rent["client_telegram"] or ""
    )
    await cb.message.answer(
        f"🔄 Продление аренды для {serial} ({device['type']})\n"
        f"Клиент: {rent['client_name']}\n"
        f"Адрес: {rent['client_address']}\n"
        f"Текущая аренда: {rent['start_date'].strftime('%d.%m.%Y')} на {rent['days']} дней, сумма {int(rent['rent_amount'])}₽\n"
        f"Дата начала продления: {start_date.strftime('%d.%m.%Y')} (автоматически)"
    )
    await cb.message.answer("🔢 На сколько дней продлить аренду?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(RentStates.entering_days)
    await cb.answer()

@router.callback_query(F.data.startswith("finishrent_"))
async def finish_rent_action(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("finishrent_", "")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rent = await conn.fetchrow("SELECT id, client_name, client_address, start_date, days, rent_amount FROM rents WHERE device_serial_number = $1 AND status = 'активна' ORDER BY start_date DESC LIMIT 1", serial)
        if not rent:
            await cb.answer("Активная аренда не найдена", show_alert=True)
            return
        device = await conn.fetchrow("SELECT serial_number, type FROM devices WHERE serial_number = $1", serial)
        if not device:
            await cb.answer("Устройство не найдено", show_alert=True)
            return
    await state.update_data(finish_rent_id=rent["id"], finish_rent_serial=serial, finish_rent_type=device["type"], finish_rent_client=rent["client_name"], finish_rent_address=rent["client_address"], finish_rent_start=rent["start_date"], finish_rent_days=rent["days"], finish_rent_amount=rent["rent_amount"])
    text = (
        f"❗️ Подтвердите завершение аренды:\n"
        f"ПК: 💻 {serial} ({device['type']})\n"
        f"Клиент: 👤 {rent['client_name']}\n"
        f"Адрес: 🏠 {rent['client_address']}\n"
        f"Период: {rent['start_date'].strftime('%d.%m.%Y')} на {rent['days']} дней\n"
        f"Сумма: 💸 {int(rent['rent_amount'])}₽\n\n"
        f"Вы уверены, что хотите завершить аренду?"
    )
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Подтвердить завершение")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await cb.message.answer(text, reply_markup=kb)
    await state.set_state(FinishRentStates.confirming)
    await cb.answer()

@router.message(FinishRentStates.confirming)
async def finish_rent_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Завершение аренды отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить завершение":
        data = await state.get_data()
        rent_id = data.get("finish_rent_id")
        serial = data.get("finish_rent_serial")
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE rents SET status = 'завершена' WHERE id = $1", rent_id)
            await conn.execute("UPDATE devices SET status = 'Свободен' WHERE serial_number = $1", serial)
        await message.answer("✅ Аренда завершена. Устройство теперь свободно.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить завершение' или 'Отмена'.")

@router.message(Command("agenda"))
async def manual_agenda(message: Message):
    if str(message.from_user.id) not in get_admins():
        await message.answer("⛔️ Только для администраторов.")
        return
    await send_agenda(message.bot, [message.from_user.id])

@router.callback_query(F.data.startswith("repair_"))
async def start_repair(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("repair_", "")
    await state.update_data(repair_serial=serial)
    await cb.message.answer(
        "🛠️ Оформление ремонта\nПожалуйста, опишите проблему (что сломалось):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(RepairStates.entering_comment)
    await cb.answer()

@router.message(RepairStates.entering_comment)
async def repair_comment(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление ремонта отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(repair_comment=message.text)
    text = f"Подтвердите оформление ремонта:\n\nПроблема: {message.text}"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Подтвердить")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer(text, reply_markup=kb)
    await state.set_state(RepairStates.confirming)

@router.message(RepairStates.confirming)
async def repair_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Оформление ремонта отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить":
        data = await state.get_data()
        serial = data.get("repair_serial")
        problem_comment = data.get("repair_comment")
        await create_repair(serial, problem_comment)
        await message.answer(f"🛠️ Ремонт оформлен для устройства {serial}!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить' или 'Отмена'.")

@router.callback_query(F.data.startswith("finishrepair_"))
async def start_finish_repair(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("finishrepair_", "")
    await state.update_data(finish_repair_serial=serial)
    await cb.message.answer(
        "✅ Завершение ремонта\nОпишите, что было сделано (комментарий):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(RepairStates.entering_finish_comment)
    await cb.answer()

@router.message(RepairStates.entering_finish_comment)
async def finish_repair_comment(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Завершение ремонта отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(finish_repair_comment=message.text)
    text = f"Подтвердите завершение ремонта:\n\nЧто сделано: {message.text}"
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Подтвердить")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer(text, reply_markup=kb)
    await state.set_state(RepairStates.confirming_finish)

@router.message(RepairStates.confirming_finish)
async def finish_repair_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Завершение ремонта отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить":
        data = await state.get_data()
        serial = data.get("finish_repair_serial")
        solution_comment = data.get("finish_repair_comment")
        await finish_repair(serial, solution_comment)
        await message.answer(f"✅ Ремонт завершён для устройства {serial}!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить' или 'Отмена'.")

@router.callback_query(F.data.startswith("comment_"))
async def start_device_comment(cb: CallbackQuery, state: FSMContext):
    serial = cb.data.replace("comment_", "")
    await state.update_data(comment_serial=serial)
    await cb.message.answer(
        "💬 Введите новый комментарий для устройства:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(CommentStates.entering_comment)
    await cb.answer()

@router.message(CommentStates.entering_comment)
async def save_device_comment(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление комментария отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    data = await state.get_data()
    serial = data.get("comment_serial")
    await add_device_comment(serial, message.text)
    await message.answer(f"✅ Комментарий добавлен для устройства {serial}!", reply_markup=ReplyKeyboardRemove())
    await send_main_menu(message)
    await state.clear()
    # Обновить карточку устройства
    fake_cb = CallbackQuery(id="0", from_user=message.from_user, data=f"device_{serial}", message=message)
    await show_device_card(fake_cb, FSMContext)

# Главное меню с кнопками
main_menu_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Список устройств"), KeyboardButton(text="📝 Оформить аренду")],
        [KeyboardButton(text="🗓️ Адженда"), KeyboardButton(text="⏰ Напоминалка")],
        [KeyboardButton(text="➕ Добавить ПК"), KeyboardButton(text="➖ Удалить ПК")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)
main_menu_user = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Список устройств"), KeyboardButton(text="📝 Оформить аренду")],
        [KeyboardButton(text="🗓️ Адженда")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

# Вспомогательная функция для отправки главного меню
async def send_main_menu(message: Message):
    is_admin = str(message.from_user.id) in get_admins()
    await message.answer("Возврат в меню", reply_markup=main_menu_admin if is_admin else main_menu_user)

@router.message(Command("menu"))
@router.message(Command("start"))
async def show_main_menu(message: Message):
    is_admin = str(message.from_user.id) in get_admins()
    await message.answer("Главное меню:", reply_markup=main_menu_admin if is_admin else main_menu_user)

# Обработчики для кнопок меню
@router.message(lambda m: m.text == "📋 Список устройств")
async def menu_devices(message: Message):
    await show_devices_list(message, status_filter="all")

@router.message(lambda m: m.text == "📝 Оформить аренду")
async def menu_rent(message: Message, state: FSMContext):
    await start_rent(message, state)

@router.message(lambda m: m.text == "🗓️ Адженда")
async def menu_agenda(message: Message):
    await manual_agenda(message)

@router.message(lambda m: m.text == "ℹ️ Помощь")
async def menu_help(message: Message):
    await message.answer("ℹ️ Справка по функциям бота: ... (добавьте описание по необходимости)")

@router.message(Command("reminder"))
async def manual_reminder(message: Message):
    if str(message.from_user.id) not in get_admins():
        await message.answer("⛔️ Только для администраторов.")
        return
    await send_reminder(message.bot, [message.from_user.id], days_ahead=3)

@router.message(Command("add_device"))
async def add_device_start(message: Message, state: FSMContext):
    if str(message.from_user.id) not in get_admins():
        await message.answer("⛔️ Только для администраторов.")
        return
    await message.answer("Введите серийный номер нового ПК:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddDeviceStates.entering_serial)

@router.message(AddDeviceStates.entering_serial)
async def add_device_serial(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(device_serial=message.text.strip())
    await message.answer("Введите тип устройства (например, PREMIUM, X и т.д.):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddDeviceStates.entering_type)

@router.message(AddDeviceStates.entering_type)
async def add_device_type(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    await state.update_data(device_type=message.text.strip())
    await message.answer("Введите дату покупки (ДД.ММ.ГГГГ):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddDeviceStates.entering_date)

@router.message(AddDeviceStates.entering_date)
async def add_device_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    try:
        purchase_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except Exception:
        await message.answer("❗️ Введите дату в формате ДД.ММ.ГГГГ.")
        return
    await state.update_data(device_purchase_date=purchase_date)
    await message.answer("Введите сумму покупки (только число):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddDeviceStates.entering_price)

@router.message(AddDeviceStates.entering_price)
async def add_device_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except Exception:
        await message.answer("❗️ Введите корректную сумму (только число, больше 0).")
        return
    await state.update_data(device_purchase_price=price)
    await message.answer("Введите базовую стоимость аренды в день (только число):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddDeviceStates.entering_base_rent)

@router.message(AddDeviceStates.entering_base_rent)
async def add_device_base_rent(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    try:
        base_rent = float(message.text.strip().replace(",", "."))
        if base_rent <= 0:
            raise ValueError
    except Exception:
        await message.answer("❗️ Введите корректную стоимость аренды (только число, больше 0).")
        return
    await state.update_data(device_base_rent=base_rent)
    data = await state.get_data()
    text = (
        f"Проверьте данные нового устройства:\n"
        f"Серийный номер: {data.get('device_serial')}\n"
        f"Тип: {data.get('device_type')}\n"
        f"Дата покупки: {data.get('device_purchase_date').strftime('%d.%m.%Y')}\n"
        f"Сумма покупки: {int(data.get('device_purchase_price'))}₽\n"
        f"Базовая аренда в день: {data.get('device_base_rent')}₽\n\n"
        f"Добавить это устройство?"
    )
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Подтвердить добавление")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer(text, reply_markup=kb)
    await state.set_state(AddDeviceStates.confirming)

@router.message(AddDeviceStates.confirming)
async def add_device_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Добавление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить добавление":
        data = await state.get_data()
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO devices (serial_number, type, purchase_date, purchase_amount, base_rent_per_day, status) VALUES ($1, $2, $3, $4, $5, 'Свободен')",
                data.get('device_serial'), data.get('device_type'), data.get('device_purchase_date'), data.get('device_purchase_price'), data.get('device_base_rent')
            )
        await message.answer("✅ Устройство успешно добавлено!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить добавление' или 'Отмена'.")

@router.message(Command("delete_device"))
async def delete_device_start(message: Message, state: FSMContext):
    if str(message.from_user.id) not in get_admins():
        await message.answer("⛔️ Только для администраторов.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT serial_number, type FROM devices ORDER BY serial_number")
    if not rows:
        await message.answer("❗️ Нет устройств для удаления.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"{r['serial_number']} ({r['type']})")] for r in rows] + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Выберите устройство для удаления или введите его серийный номер:", reply_markup=kb)
    await state.set_state(DeleteDeviceStates.choosing)

@router.message(DeleteDeviceStates.choosing)
async def delete_device_choose(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Удаление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    serial = message.text.split()[0] if " " in message.text else message.text.strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        device = await conn.fetchrow("SELECT serial_number, type, purchase_date, purchase_amount, base_rent_per_day, status FROM devices WHERE serial_number = $1", serial)
    if not device:
        await message.answer("❗️ Устройство не найдено. Введите корректный серийный номер или выберите из списка.")
        return
    await state.update_data(delete_serial=serial)
    text = (
        f"❗️ Подтвердите удаление устройства:\n"
        f"Серийный номер: {device['serial_number']}\n"
        f"Тип: {device['type']}\n"
        f"Дата покупки: {device['purchase_date'].strftime('%d.%m.%Y')}\n"
        f"Сумма покупки: {int(device['purchase_amount'])}₽\n"
        f"Базовая аренда в день: {device['base_rent_per_day']}₽\n"
        f"Статус: {device['status']}\n\n"
        f"Вы уверены, что хотите удалить это устройство?"
    )
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Подтвердить удаление")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer(text, reply_markup=kb)
    await state.set_state(DeleteDeviceStates.confirming)

@router.message(DeleteDeviceStates.confirming)
async def delete_device_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("🚫 Удаление отменено.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
        return
    if message.text == "✅ Подтвердить удаление":
        data = await state.get_data()
        serial = data.get("delete_serial")
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM devices WHERE serial_number = $1", serial)
        await message.answer("✅ Устройство успешно удалено!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(message)
        await state.clear()
    else:
        await message.answer("⚠️ Пожалуйста, выберите 'Подтвердить удаление' или 'Отмена'.")

@router.message(lambda m: m.text == "➕ Добавить ПК")
async def menu_add_device(message: Message, state: FSMContext):
    await add_device_start(message, state)

@router.message(lambda m: m.text == "➖ Удалить ПК")
async def menu_delete_device(message: Message, state: FSMContext):
    await delete_device_start(message, state)

@router.message(lambda m: m.text == "⏰ Напоминалка")
async def menu_reminder(message: Message):
    await manual_reminder(message) 