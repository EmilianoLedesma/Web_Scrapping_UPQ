# Telegram Bot - UPQ Grade Monitoring

Telegram bot for remote access to UPQ Sistema Integral grades and academic data.

## Features

- Real-time grade consultation
- Automatic change detection
- Historical statistics
- Secure authentication with UPQ system
- Conversational Telegram interface

## Installation

### Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

This will install `python-telegram-bot` along with other project dependencies.

### Configuration

The Telegram bot token is configured in the `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

To create a new bot:

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the provided token to your `.env` file

### Running the Bot

```bash
# Windows
$env:PYTHONIOENCODING='utf-8'; python run_bot.py

# Linux/macOS
python run_bot.py
```

The bot will start and listen for commands.

## Available Commands

### `/start`

Initialize the bot and display welcome message.

### `/grades`

Fetch current grades from UPQ system.

**Example response:**

```
CALIFICACIONES

EMILIANO LEDESMA
Matrícula: 123046244
Periodo: SEPTIEMBRE-DICIEMBRE 2025
Consulta: 2025-11-08T19:40:00

LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO
Profesor: RAMIREZ RESENDIZ ADRIANA KARINA
Grupo: S204-7
Calificaciones: P1: 9.35 | P2: 9.20 | P3: --
```

### `/check`

Check for new grades since last query.

**Example response (with changes):**

```
Se detectaron 2 cambios

LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO
P2: -- → 9.20
Timestamp: 2025-11-08T19:40:00Z

PROGRAMACIÓN WEB
P1: 8.5 → 9.0
Timestamp: 2025-11-08T19:40:00Z
```

### `/stats`

Display system statistics.

**Example response:**

```
Estadísticas del Sistema

Total de snapshots: 5
Total de cambios detectados: 3
Última verificación: 2025-11-08T19:40:00Z
Primer snapshot: 2025-11-01T10:00:00Z
```

### `/help`

Show help information with all available commands.

## Architecture

### Execution Flow

1. User sends command → Bot receives message
2. Bot processes command → Executes corresponding function
3. UPQ system connection → Authentication and scraping
4. Data parsing → Extracts grades from HTML
5. Storage → Saves snapshot for comparisons
6. User response → Sends formatted message

### Components

```
bot/telegram_bot.py
├── UPQTelegramBot (Main class)
│   ├── start_command()      # /start command
│   ├── help_command()       # /help command
│   ├── grades_command()     # /grades command
│   ├── check_command()      # /check command
│   ├── stats_command()      # /stats command
│   └── error_handler()      # Error handling
│
├── Integration with existing modules:
│   ├── config.settings      # Configuration
│   ├── scraper.fetcher      # HTTP requests
│   ├── scraper.parser       # HTML parsing
│   ├── scraper.auth         # Authentication
│   └── storage.memory       # Persistence
```

## Error Handling

The bot automatically handles:

- Invalid credentials
- UPQ system downtime
- Session expiration
- HTML format changes
- Network errors

## Security

- Bot does NOT store passwords, uses credentials from `.env`
- Encrypted communication with Telegram (HTTPS)
- Error logging without exposing credentials
- Personal use bot (not public)

## Deployment

### 24/7 Operation

For continuous operation, consider:

**Option 1: VPS Server** (DigitalOcean, AWS, etc.)

**Option 2: tmux/screen**

```bash
# Start tmux session
tmux new -s telegram-bot

# Run bot
python run_bot.py

# Detach: Ctrl+B, then D
# Re-attach: tmux attach -t telegram-bot
```

**Option 3: systemd Service** (Linux)

Create `/etc/systemd/system/upq-bot.service`:

```ini
[Unit]
Description=UPQ Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/python run_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable upq-bot
sudo systemctl start upq-bot
```

## Troubleshooting

### Error: python-telegram-bot not installed

```bash
pip install python-telegram-bot==20.7
```

### Error: TELEGRAM_BOT_TOKEN not configured

Verify `.env` contains:

```env
TELEGRAM_BOT_TOKEN=your_token_here
```

### Bot not responding

1. Check bot is running (no errors in terminal)
2. Ensure you've started a conversation with the bot
3. Verify token is correct

### UPQ authentication errors

Verify credentials in `.env`:

```env
UPQ_USERNAME=your_student_id
UPQ_PASSWORD=your_password
```

## Future Improvements

- Automatic push notifications (periodic polling)
- Multi-user support
- Administrative commands
- Configurable check intervals
- PDF grade export
- Grade evolution charts

## Logs

Bot logs appear in terminal with format:

```
2025-11-08 19:40:00 - telegram.ext.Application - INFO - Application started
2025-11-08 19:40:05 - __main__ - INFO - Comando /grades ejecutado
```

To save logs to file:

```bash
python run_bot.py 2>&1 | tee bot.log
```

## Contact

Developed by Emiliano Ledesma

For help, see [Main README](../README.md)
