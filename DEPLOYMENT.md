# 🚀 Инструкция по развертыванию XRent Bot 2.0

## 📋 Предварительные требования

### Системные требования
- **ОС**: Linux (Ubuntu 20.04+), Windows 10+, macOS 10.15+
- **Python**: 3.12 или выше
- **PostgreSQL**: 12 или выше
- **RAM**: минимум 512MB (рекомендуется 1GB+)
- **Дисковое пространство**: минимум 100MB

### Необходимые инструменты
- Git
- pip (Python package manager)
- psql (PostgreSQL client)

## 🔧 Пошаговое развертывание

### 1. Подготовка системы

#### Ubuntu/Debian:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и pip
sudo apt install python3.12 python3.12-pip python3.12-venv -y

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка Git
sudo apt install git -y
```

#### Windows:
1. Скачайте и установите Python 3.12 с [python.org](https://python.org)
2. Скачайте и установите PostgreSQL с [postgresql.org](https://postgresql.org)
3. Скачайте и установите Git с [git-scm.com](https://git-scm.com)

#### macOS:
```bash
# Установка Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка Python
brew install python@3.12

# Установка PostgreSQL
brew install postgresql

# Установка Git
brew install git
```

### 2. Клонирование проекта

```bash
# Клонирование репозитория
git clone <repository-url>
cd XRent-Bot-Finale

# Создание виртуального окружения
python3.12 -m venv venv

# Активация виртуального окружения
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt
```

### 4. Настройка базы данных

#### Создание базы данных:
```bash
# Подключение к PostgreSQL
sudo -u postgres psql

# Создание пользователя (замените username и password)
CREATE USER xrent_user WITH PASSWORD 'your_secure_password';

# Создание базы данных
CREATE DATABASE xrent_db OWNER xrent_user;

# Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE xrent_db TO xrent_user;

# Выход из psql
\q
```

#### Инициализация таблиц:
```bash
# Выполнение скрипта создания таблиц
psql -h localhost -U xrent_user -d xrent_db -f init_db.sql

# Выполнение скрипта оптимизации (рекомендуется)
psql -h localhost -U xrent_user -d xrent_db -f optimize_db.sql
```

### 5. Настройка конфигурации

#### Создание конфигурационных файлов:
```bash
# Создание папки config
mkdir -p config

# Создание файла .env
cat > config/.env << EOF
TELEGRAM_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=xrent_db
DB_USER=xrent_user
DB_PASSWORD=your_secure_password
EOF

# Создание файла admins.txt
cat > config/admins.txt << EOF
123456789
987654321
EOF
```

#### Получение Telegram Bot Token:
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в `config/.env`

#### Добавление администраторов:
1. Найдите свой Telegram ID (используйте @userinfobot)
2. Добавьте ID в файл `config/admins.txt` (по одному на строку)

### 6. Тестирование

```bash
# Запуск бота в тестовом режиме
python -m bot.main
```

Проверьте:
- ✅ Бот отвечает на команду `/start`
- ✅ Отображается главное меню
- ✅ Нет ошибок в консоли
- ✅ Создаются логи в папке `logs/`

### 7. Настройка автозапуска

#### Linux (systemd):
```bash
# Создание сервиса
sudo cat > /etc/systemd/system/xrent-bot.service << EOF
[Unit]
Description=XRent Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/XRent-Bot-Finale
Environment=PATH=/path/to/XRent-Bot-Finale/venv/bin
ExecStart=/path/to/XRent-Bot-Finale/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Включение и запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable xrent-bot
sudo systemctl start xrent-bot

# Проверка статуса
sudo systemctl status xrent-bot
```

#### Windows (Task Scheduler):
1. Откройте "Планировщик задач"
2. Создайте новую задачу
3. Настройте запуск при старте системы
4. Укажите путь к Python и скрипту

#### macOS (launchd):
```bash
# Создание plist файла
cat > ~/Library/LaunchAgents/com.xrent.bot.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.xrent.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/XRent-Bot-Finale/venv/bin/python</string>
        <string>-m</string>
        <string>bot.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/XRent-Bot-Finale</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Загрузка сервиса
launchctl load ~/Library/LaunchAgents/com.xrent.bot.plist
```

## 🔍 Мониторинг и обслуживание

### Просмотр логов:
```bash
# Общие логи
tail -f logs/xrent_bot.log

# Ошибки
tail -f logs/errors.log

# Действия пользователей
tail -f logs/user_actions.log
```

### Обновление бота:
```bash
# Остановка сервиса
sudo systemctl stop xrent-bot  # Linux
# или остановка вручную

# Обновление кода
git pull origin main

# Обновление зависимостей
pip install -r requirements.txt

# Запуск сервиса
sudo systemctl start xrent_bot  # Linux
```

### Резервное копирование:
```bash
# Создание бэкапа базы данных
pg_dump -h localhost -U xrent_user xrent_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
psql -h localhost -U xrent_user xrent_db < backup_file.sql
```

## 🛠️ Устранение неполадок

### Частые проблемы:

#### 1. Ошибка подключения к базе данных
```bash
# Проверка статуса PostgreSQL
sudo systemctl status postgresql

# Проверка подключения
psql -h localhost -U xrent_user -d xrent_db
```

#### 2. Ошибка токена Telegram
- Проверьте правильность токена в `config/.env`
- Убедитесь, что бот не заблокирован

#### 3. Ошибки прав доступа
```bash
# Проверка прав на файлы
ls -la config/
chmod 600 config/.env
chmod 644 config/admins.txt
```

#### 4. Проблемы с логированием
```bash
# Создание папки логов
mkdir -p logs
chmod 755 logs
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в папке `logs/`
2. Убедитесь в правильности конфигурации
3. Проверьте системные требования
4. Создайте Issue на GitHub с подробным описанием проблемы

## 🔒 Безопасность

### Рекомендации:
- ✅ Используйте сложные пароли для базы данных
- ✅ Ограничьте доступ к серверу только необходимыми портами
- ✅ Регулярно обновляйте систему и зависимости
- ✅ Настройте firewall
- ✅ Используйте SSL для подключения к базе данных
- ✅ Регулярно создавайте резервные копии 