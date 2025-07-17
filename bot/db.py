import os
# NOTE: Linter error on 'import asyncpg' can be ignored if asyncpg is installed in your environment.
from dotenv import load_dotenv
from typing import List, Dict, Optional
from datetime import date, timedelta
import asyncpg  # NOTE: Linter error can be ignored if asyncpg is installed in your environment.

load_dotenv("config/.env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    return _pool

async def get_free_devices() -> List[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT serial_number, type FROM devices WHERE status = 'Свободен'")
        return [{"serial_number": r["serial_number"], "type": r["type"]} for r in rows]

async def get_base_rent(serial_number: str) -> Optional[float]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT base_rent_per_day FROM devices WHERE serial_number = $1", serial_number)
        return float(row["base_rent_per_day"]) if row else None

async def create_rent(device_serial_number: str, client_fio: str, client_address: str, start_date, days: int, rent_amount: float, coefficient: Optional[float], discount_percent: float = 0.0, client_phone: str = '', client_telegram: str = ''):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO rents (device_serial_number, client_name, client_address, start_date, days, rent_amount, coefficient, discount_percent, client_phone, client_telegram, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'активна')
            """,
            device_serial_number, client_fio, client_address, start_date, days, rent_amount, coefficient, discount_percent, client_phone, client_telegram
        )
        await conn.execute(
            "UPDATE devices SET status = 'В аренде' WHERE serial_number = $1",
            device_serial_number
        )

async def get_device_info(serial_number: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        device = await conn.fetchrow("SELECT * FROM devices WHERE serial_number = $1", serial_number)
        if not device:
            return None
        # Сумма всех аренд
        total_rent = await conn.fetchval("SELECT COALESCE(SUM(rent_amount), 0) FROM rents WHERE device_serial_number = $1", serial_number)
        # Сумма покупки
        purchase_amount = device["purchase_amount"]
        # Прибыль
        profit = float(total_rent) - float(purchase_amount)
        # Суммарные дни в аренде
        total_rent_days = await conn.fetchval("SELECT COALESCE(SUM(days), 0) FROM rents WHERE device_serial_number = $1", serial_number)
        # Суммарные дни в ремонте (по количеству записей, если нужно по датам — доработать)
        total_repair_days = await conn.fetchval("SELECT COUNT(*) FROM repairs WHERE device_serial_number = $1", serial_number)
        # Суммарные дни в простое (пример: общее время существования минус аренда и ремонт)
        # Для MVP: просто 0, доработаем позже
        total_idle_days = 0
        return {
            "serial_number": device["serial_number"],
            "type": device["type"],
            "status": device["status"],
            "purchase_date": device["purchase_date"],
            "purchase_amount": float(purchase_amount),
            "profit": profit,
            "comments": device["comments"],
            "total_rent_days": total_rent_days,
            "total_repair_days": total_repair_days,
            "total_idle_days": total_idle_days
        }

async def get_rent_history(serial_number: str, offset: int = 0, limit: int = 5, desc: bool = True) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        order = 'DESC' if desc else 'ASC'
        rows = await conn.fetch(
            f"SELECT start_date, days, client_name, rent_amount, status FROM rents WHERE device_serial_number = $1 ORDER BY start_date {order} OFFSET $2 LIMIT $3",
            serial_number, offset, limit
        )
        return [dict(r) for r in rows]

async def get_rent_history_count(serial_number: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM rents WHERE device_serial_number = $1", serial_number)

async def get_repair_history(serial_number: str, offset: int = 0, limit: int = 5) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT repair_date, comment FROM repairs WHERE device_serial_number = $1 ORDER BY repair_date DESC OFFSET $2 LIMIT $3",
            serial_number, offset, limit
        )
        return [dict(r) for r in rows]

async def get_repair_history_count(serial_number: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM repairs WHERE device_serial_number = $1", serial_number)

async def get_rent_last_date(serial_number: str) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT MAX(start_date) FROM rents WHERE device_serial_number = $1", serial_number)

async def get_repair_last_date(serial_number: str) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT MAX(repair_date) FROM repairs WHERE device_serial_number = $1", serial_number)

async def get_rents_ending_today() -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        today = date.today()
        rows = await conn.fetch(
            """
            SELECT r.id, r.device_serial_number, d.type, r.client_name, r.client_address, r.start_date, r.days, r.rent_amount, r.status, r.client_phone, r.client_telegram
            FROM rents r
            JOIN devices d ON r.device_serial_number = d.serial_number
            WHERE r.status = 'активна' AND (r.start_date + (r.days - 1) * INTERVAL '1 day') = $1
            """,
            today
        )
        return [dict(row) for row in rows]

async def get_overdue_rents() -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        today = date.today()
        rows = await conn.fetch(
            """
            SELECT r.id, r.device_serial_number, d.type, r.client_name, r.client_address, r.start_date, r.days, r.rent_amount, r.status, r.client_phone, r.client_telegram
            FROM rents r
            JOIN devices d ON r.device_serial_number = d.serial_number
            WHERE r.status = 'активна' AND (r.start_date + (r.days - 1) * INTERVAL '1 day') <= $1
            ORDER BY r.start_date
            """,
            today
        )
        return [dict(row) for row in rows]

async def create_repair(device_serial_number: str, problem_comment: str):
    """
    Оформить ремонт: создать запись в repairs с problem_comment и перевести устройство в статус 'На ремонте'.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO repairs (device_serial_number, repair_date, problem_comment, status)
            VALUES ($1, CURRENT_DATE, $2, 'в процессе')
            """,
            device_serial_number, problem_comment
        )
        await conn.execute(
            "UPDATE devices SET status = 'На ремонте' WHERE serial_number = $1",
            device_serial_number
        )

async def finish_repair(device_serial_number: str, solution_comment: str):
    """
    Завершить ремонт: обновить последнюю запись repairs (добавить solution_comment, дату окончания, статус) и перевести устройство в статус 'Свободен'.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Найти id последней незавершённой записи ремонта
        repair_id = await conn.fetchval(
            """
            SELECT id FROM repairs
            WHERE device_serial_number = $1 AND status = 'в процессе'
            ORDER BY repair_date DESC LIMIT 1
            """,
            device_serial_number
        )
        if repair_id is not None:
            await conn.execute(
                """
                UPDATE repairs
                SET finish_date = CURRENT_DATE, solution_comment = $2, status = 'завершён'
                WHERE id = $1
                """,
                repair_id, solution_comment
            )
            await conn.execute(
                "UPDATE devices SET status = 'Свободен' WHERE serial_number = $1",
                device_serial_number
            )

async def add_device_comment(serial_number: str, comment: str):
    """
    Добавить комментарий к устройству: сохраняет в device_comments и обновляет поле comments в devices.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_comments (serial_number, comment) VALUES ($1, $2)
            """,
            serial_number, comment
        )
        await conn.execute(
            "UPDATE devices SET comments = $2 WHERE serial_number = $1",
            serial_number, comment
        )

async def get_last_device_comment(serial_number: str) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT comment FROM device_comments WHERE serial_number = $1 ORDER BY created_at DESC LIMIT 1",
            serial_number
        )
        return row["comment"] if row else "-"

async def get_device_comments(serial_number: str) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT comment, created_at FROM device_comments WHERE serial_number = $1 ORDER BY created_at DESC",
            serial_number
        )
        return [{"comment": r["comment"], "created_at": r["created_at"]} for r in rows]

async def get_device_stats() -> dict:
    """
    Возвращает количество устройств по статусам: в аренде, в ремонте, свободных.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        in_rent = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE status = 'В аренде'")
        in_repair = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE status = 'На ремонте'")
        free = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE status = 'Свободен'")
    return {"in_rent": in_rent, "in_repair": in_repair, "free": free}

async def get_month_revenue() -> float:
    """
    Возвращает сумму выручки за текущий месяц по всем активным и завершённым арендам.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        today = date.today()
        first_day = today.replace(day=1)
        revenue = await conn.fetchval(
            "SELECT COALESCE(SUM(rent_amount), 0) FROM rents WHERE start_date >= $1",
            first_day
        )
    return float(revenue)

async def get_rents_ending_soon(days_ahead: int = 3) -> list:
    """
    Возвращает список аренд, которые завершатся в ближайшие days_ahead дней (включительно, включая сегодня).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        rows = await conn.fetch(
            """
            SELECT r.id, r.device_serial_number, d.type, r.client_name, r.client_address, r.start_date, r.days, r.rent_amount, r.status, r.client_phone, r.client_telegram
            FROM rents r
            JOIN devices d ON r.device_serial_number = d.serial_number
            WHERE r.status = 'активна'
              AND (r.start_date + (r.days - 1) * INTERVAL '1 day') >= $1
              AND (r.start_date + (r.days - 1) * INTERVAL '1 day') <= $2
            ORDER BY r.start_date
            """,
            today, end_date
        )
    return [dict(row) for row in rows]

# Пример использования:
# pool = await get_pool()
# async with pool.acquire() as conn:
#     result = await conn.fetch('SELECT 1') 