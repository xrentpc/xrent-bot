-- Оптимизация базы данных XRent Bot (исправленная версия)
-- Выполните этот скрипт для улучшения производительности

-- Индексы для таблицы devices
CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(type);

-- Индексы для таблицы rents
CREATE INDEX IF NOT EXISTS idx_rents_device_serial ON rents(device_serial_number);
CREATE INDEX IF NOT EXISTS idx_rents_status ON rents(status);
CREATE INDEX IF NOT EXISTS idx_rents_start_date ON rents(start_date);
CREATE INDEX IF NOT EXISTS idx_rents_client_name ON rents(client_name);
CREATE INDEX IF NOT EXISTS idx_rents_expected_payment_date ON rents(expected_payment_date);
CREATE INDEX IF NOT EXISTS idx_rents_debt_status ON rents(debt_status);

-- Составной индекс для поиска активных аренд по дате
CREATE INDEX IF NOT EXISTS idx_rents_active_date ON rents(status, start_date) WHERE status = 'активна';

-- Составной индекс для поиска долгов
CREATE INDEX IF NOT EXISTS idx_rents_debt_search ON rents(debt_status, expected_payment_date) 
WHERE debt_status IS NOT NULL AND expected_payment_date IS NOT NULL;

-- Индексы для таблицы repairs
CREATE INDEX IF NOT EXISTS idx_repairs_device_serial ON repairs(device_serial_number);
CREATE INDEX IF NOT EXISTS idx_repairs_repair_date ON repairs(repair_date);
CREATE INDEX IF NOT EXISTS idx_repairs_status ON repairs(status);

-- Индексы для таблицы debt_payments
CREATE INDEX IF NOT EXISTS idx_debt_payments_rent_id ON debt_payments(rent_id);
CREATE INDEX IF NOT EXISTS idx_debt_payments_paid_at ON debt_payments(paid_at);

-- Индексы для таблицы device_comments
CREATE INDEX IF NOT EXISTS idx_device_comments_serial ON device_comments(serial_number);
CREATE INDEX IF NOT EXISTS idx_device_comments_created_at ON device_comments(created_at);

-- Индексы для таблицы comments
CREATE INDEX IF NOT EXISTS idx_comments_device_serial ON comments(device_serial_number);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Индексы для таблицы admins
CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id);

-- GIN индекс для JSONB поля peripherals
CREATE INDEX IF NOT EXISTS idx_rents_peripherals_gin ON rents USING GIN (peripherals);

-- Статистика для оптимизатора запросов
ANALYZE devices;
ANALYZE rents;
ANALYZE repairs;
ANALYZE debt_payments;
ANALYZE device_comments;
ANALYZE comments;
ANALYZE admins;

-- Комментарии к индексам
COMMENT ON INDEX idx_devices_serial_number IS 'Быстрый поиск устройств по серийному номеру';
COMMENT ON INDEX idx_devices_status IS 'Фильтрация устройств по статусу';
COMMENT ON INDEX idx_rents_device_serial IS 'Поиск аренд по устройству';
COMMENT ON INDEX idx_rents_active_date IS 'Поиск активных аренд по дате';
COMMENT ON INDEX idx_rents_debt_search IS 'Поиск долгов по статусу и дате оплаты';
COMMENT ON INDEX idx_rents_peripherals_gin IS 'Поиск по периферийным устройствам (JSONB)'; 