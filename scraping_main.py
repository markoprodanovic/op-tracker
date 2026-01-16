"""
Main execution module for the One Piece episode scraping feature.

This module provides the main entry point for running the scraping service
that fetches episode data from animefillerlist.com and stores it in Supabase.
"""

from src.scraping.scraping_service import sync_one_piece_episodes
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add src to Python path
sys.path.append(str(Path(__file__).parent))


async def main():
    """Main entry point for the scraping service."""
    logger.info("🏴‍☠️ One Piece Episode Scraper - Starting")

    try:
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )

        # Run the sync process
        stats = await sync_one_piece_episodes()

        # Log final results
        if stats["episodes_inserted"] > 0:
            logger.success(f"🎉 Successfully added {stats['episodes_inserted']} new episodes!")
        elif stats["new_episodes_found"] == 0:
            logger.info("✅ Database is already up to date - no new episodes found")
        else:
            logger.warning(f"⚠️ Found {stats['new_episodes_found']} new episodes but failed to insert them")

        return 0  # Success exit code

    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        return 1  # Error exit code


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
