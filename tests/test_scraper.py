#!/usr/bin/env python3
"""
Simple test script to verify the scraper works.
Run this to test the scraping functionality before integrating with the database.
"""

from src.scraping.scraper import scrape_one_piece_episodes
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))


async def test_scraper():
    """Test the scraper and show some results."""
    print("🚀 Testing One Piece episode scraper...")

    try:
        episodes = await scrape_one_piece_episodes()

        print(f"✅ Successfully scraped {len(episodes)} episodes!")
        print("\n📺 First 5 episodes:")
        for episode in episodes[:5]:
            print(f"  Episode {episode['id']}: {episode['title']}")
            print(f"    Airdate: {episode['airdate']}")
            print()

        print("\n📺 Last 5 episodes:")
        for episode in episodes[-5:]:
            print(f"  Episode {episode['id']}: {episode['title']}")
            print(f"    Airdate: {episode['airdate']}")
            print()

        return episodes

    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return None


if __name__ == "__main__":
    episodes = asyncio.run(test_scraper())
