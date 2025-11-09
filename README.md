# UPQ Sistema Integral - Web Scraper

Automated web scraping system for extracting and monitoring academic data from Universidad Politécnica de Querétaro (UPQ) Sistema Integral.

## Features

- **Telegram Bot Integration** - Natural language processing for conversational queries
- **Automated Authentication** - Persistent session management with cookie handling
- **Robust HTML Parsing** - CSS-agnostic parsing that adapts to layout changes
- **Change Detection** - Automatic monitoring and notification of grade updates
- **Persistent Storage** - Complete history tracking with JSON snapshots
- **CLI Interface** - Multiple command-line operations for data extraction
- **Modular Architecture** - Extensible codebase ready for API integration
- **Type Safety** - Complete type hints and comprehensive error handling

## Requirements

- Python 3.8 or higher
- Internet connection
- Valid UPQ Sistema Integral credentials

## Quick Start

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/upq-scraper.git
cd upq-scraper
```

2. **Create virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure credentials**

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` file:

```env
UPQ_USERNAME=your_student_id
UPQ_PASSWORD=your_password
TELEGRAM_BOT_TOKEN=your_telegram_bot_token  # Optional
```

## Usage

### CLI Commands

**Get current grades**

```bash
python main.py --get-grades
```

**Check for new grades**

```bash
python main.py --check-new
```

**View statistics**

```bash
python main.py --stats
```

**Export data**

```bash
python main.py --export backup.json
```

**JSON output**

```bash
python main.py --json
```

### Telegram Bot

1. **Start the bot**

```bash
python run_bot.py
```

2. **Available commands**

- `/start` - Initialize bot
- `/grades` - View current grades
- `/check` - Check for updates
- `/stats` - View statistics
- `/help` - Show help

For detailed bot documentation, see [bot/README.md](bot/README.md)

## Project Structure

```
upq-scraper/
├── config/              # Configuration management
│   └── settings.py
├── scraper/             # Core scraping logic
│   ├── auth.py         # Authentication handler
│   ├── parser.py       # HTML parser
│   └── fetcher.py      # HTTP client
├── storage/             # Data persistence
│   └── memory.py       # JSON storage handler
├── bot/                 # Telegram bot integration
│   └── telegram_bot.py
├── tests/               # Unit tests
│   └── test_scraper.py
├── tools/               # Utility scripts
├── main.py              # CLI entry point
├── run_bot.py           # Bot launcher
└── requirements.txt     # Python dependencies
```

## Architecture

### Authentication Flow

1. POST credentials to `alumnos.php/signin`
2. Maintain session using `requests.Session()` with cookies
3. Use authenticated session for all subsequent requests

### HTML Parsing Strategy

The parser is designed to be resilient to HTML changes:

- Locates tables by header content instead of CSS classes
- Identifies columns by text matching (e.g., "materia", "calificación")
- Uses flexible regex patterns
- Implements multiple fallback strategies

### Change Detection

1. Saves snapshot on each grade fetch
2. Compares with last snapshot when checking for updates
3. Detects:
   - New courses
   - New grades (null to value)
   - Updated grades (value change)

## Configuration

All settings are managed through environment variables in `.env`:

```env
# Authentication
UPQ_USERNAME=your_student_id
UPQ_PASSWORD=your_password

# System URLs
UPQ_BASE_URL=https://sistemaintegral.upq.edu.mx
UPQ_LOGIN_URL=https://sistemaintegral.upq.edu.mx/alumnos.php/signin
UPQ_GRADES_URL=https://sistemaintegral.upq.edu.mx/alumnos.php/carga-academica

# Request Configuration
REQUEST_TIMEOUT=30
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Storage
STORAGE_PATH=storage/grades_history.json
```

## Security

- Never commit `.env` file (already in `.gitignore`)
- Credentials loaded from environment variables only
- Session cookies kept in memory, not persisted to disk
- All communication over HTTPS

## Error Handling

The system handles:

- Invalid credentials validation
- Network timeouts (configurable)
- Session expiration detection
- HTML format variations
- Connection failures

## Testing

```bash
pytest tests/
```

## Development

### Adding New Features

The modular design allows easy extension:

- **New scrapers**: Add to `scraper/`
- **Export formats**: Extend `storage/memory.py`
- **Bot commands**: Implement in `bot/telegram_bot.py`
- **REST API**: Create new module in `api/`

### Type Hints

All code uses Python type hints for maintainability:

```python
def parse_grades(self) -> Dict[str, Any]:
    """Parse grades with defined types."""
    pass
```

## Roadmap

- [ ] Automated notifications via Telegram
- [ ] Multi-account support
- [ ] Web dashboard with Flask
- [ ] Grade evolution charts
- [ ] Automatic GPA calculation
- [ ] PDF export
- [ ] Email notifications
- [ ] Mobile app with React Native

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open Pull Request

## License

This project is open source and available under the MIT License.

## Disclaimer

This project is for educational and personal use only. Use responsibly and respect UPQ's terms of service.

## Author

Developed by Emiliano Ledesma

## Support

For issues or questions, please open an issue on the repository.
