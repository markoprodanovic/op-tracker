#!/usr/bin/env python3
"""
One Piece Tracker - Main Entry Point

This script provides easy access to both my original API-based sync
and the new web scraping functionality.

Usage:
    python main.py              # Run API sync (original)
    python main.py scrape       # Run web scraping sync (new)
    python main.py --help       # Show this help
"""

import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent))


def show_help():
    """Show usage help."""
    print(__doc__)


async def run_api_sync():
    """Run the original API-based sync."""
    print("🔄 Running original API-based episode sync...")
    try:
        from src.api.main import main as api_main
        await api_main()
    except ImportError:
        print("❌ API sync module not found. Make sure src/main.py exists.")
        return False
    except Exception as e:
        print(f"❌ API sync failed: {e}")
        return False
    return True


async def run_scraping_sync():
    """Run the new web scraping sync."""
    print("🌐 Running web scraping episode sync...")
    try:
        from scraping_main import main as scraping_main
        return await scraping_main()
    except ImportError:
        print("❌ Scraping module not found. Make sure scraping_main.py exists.")
        return 1
    except Exception as e:
        print(f"❌ Scraping sync failed: {e}")
        return 1


async def main():
    """Main entry point."""
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if not args or args[0] in ['api', 'original']:
        # Default: run original API sync
        success = await run_api_sync()
        return 0 if success else 1

    elif args[0] in ['scrape', 'scraping', 'web']:
        # Run web scraping sync
        return await run_scraping_sync()

    elif args[0] in ['--help', '-h', 'help']:
        # Show help
        show_help()
        return 0

    else:
        print(f"❌ Unknown command: {args[0]}")
        print("Run 'python main.py --help' for usage information.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
