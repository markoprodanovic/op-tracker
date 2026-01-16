# One Piece Episode Tracker

Python application that synchronizes One Piece episode data to a Supabase database using two methods:

1. **API-based sync** (original) - Fetches from One Piece API
2. **Web scraping** (new) - Scrapes from animefillerlist.com for more current data

## 🚀 Quick Start

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run web scraping sync (recommended)
python main.py scrape

# Run original API sync
python main.py api

# Show all options
python main.py --help
```

## 📊 Features

- **Web Scraping**: Get the latest episodes from animefillerlist.com
- **Arc Management**: Automatic assignment of episodes to story arcs
- **Incremental Updates**: Only adds new episodes (no duplicates)
- **Batch Processing**: Efficient database operations
- **Comprehensive Logging**: Detailed sync statistics and progress

## 🗄️ Database Schema

### Original Table (`episodes`)

- Current API-based episode data
- Used by existing frontend

### New Tables (`scraped_episodes`, `arcs`)

- Web-scraped episode data with arc assignments
- Future-ready for frontend migration

## 📁 Project Structure

```
├── src/                    # Core application code
│   ├── scraper.py         # Web scraping logic
│   ├── scraping_service.py # Main scraping orchestration
│   ├── scraped_database.py # Database operations for scraped data
│   ├── arc_database.py    # Arc management
│   └── models.py          # Data models
├── tests/                 # Test files
├── database/              # Database schema and setup scripts
├── docs/                  # Documentation and guides
├── main.py               # Main entry point
└── scraping_main.py      # Direct scraping entry point
```

## 🧪 Testing

```bash
# Test web scraping
python tests/test_scraper.py

# Test database integration
python tests/test_database.py

# Test complete workflow
python tests/test_workflow.py
```

## 📖 Documentation

- [Database Setup Guide](docs/DATABASE_SETUP.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
