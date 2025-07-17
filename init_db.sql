-- Если таблица уже создана, используйте:
ALTER TABLE repairs ADD COLUMN problem_comment TEXT;
ALTER TABLE repairs ADD COLUMN solution_comment TEXT;
ALTER TABLE rents ADD COLUMN client_phone VARCHAR(32);
ALTER TABLE rents ADD COLUMN client_telegram VARCHAR(64);
-- Если создаёте с нуля:
-- CREATE TABLE repairs (
--     id SERIAL PRIMARY KEY,
--     device_serial_number VARCHAR(50) NOT NULL,
--     repair_date DATE NOT NULL,
--     finish_date DATE,
--     problem_comment TEXT,
--     solution_comment TEXT,
--     status VARCHAR(20) NOT NULL,
--     ...
-- ); 

-- История комментариев к устройствам
CREATE TABLE IF NOT EXISTS device_comments (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(50) NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
); 