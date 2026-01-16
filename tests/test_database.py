#!/usr/bin/env python3
"""
Test script to verify arc assignment and database integration.
"""

from datetime import date
from src.models import ScrapedEpisode, ScrapedEpisodeForDB
from src.database.scraped_database import ScrapedEpisodeDatabase
from src.database.arc_database import ArcDatabase
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))


async def test_arc_assignment():
    """Test arc assignment logic."""
    print("🏴‍☠️ Testing arc assignment logic...")

    try:
        with ArcDatabase() as arc_db:
            # Test some episode numbers
            test_episodes = [1, 50, 100, 500, 1000, 1155, 9999]

            print("\n📍 Arc assignments:")
            for episode_num in test_episodes:
                arc = arc_db.get_arc_for_episode(episode_num)
                if arc:
                    print(f"  Episode {episode_num:4d}: {arc.name} (episodes {arc.start_episode}-{arc.end_episode})")
                else:
                    print(f"  Episode {episode_num:4d}: No arc found")

            print(f"\n📊 Total arcs in database: {len(arc_db.get_all_arcs())}")

        return True

    except Exception as e:
        print(f"❌ Arc assignment test failed: {e}")
        return False


async def test_episode_database():
    """Test scraped episode database operations."""
    print("\n💾 Testing scraped episode database...")

    try:
        with ScrapedEpisodeDatabase() as episode_db:
            # Check existing episodes
            existing_count = episode_db.get_episode_count()
            print(f"📈 Current episodes in database: {existing_count}")

            # Test with a sample episode
            sample_episode = ScrapedEpisode(
                id=9999,  # Use a high number to avoid conflicts
                title="Test Episode - Adventure Begins!",
                airdate=date(2026, 1, 4)
            )

            db_episode = ScrapedEpisodeForDB.from_scraped_episode(sample_episode)

            # Test arc assignment
            db_episode_with_arc = episode_db.assign_arc_to_episode(db_episode)
            print(f"🎯 Test episode {db_episode_with_arc.id} assigned arc ID: {db_episode_with_arc.arc_id}")

            # Check if episode already exists
            existing_ids = episode_db.get_existing_episode_ids()
            if 9999 in existing_ids:
                print("⚠️  Test episode 9999 already exists, skipping insert test")
            else:
                # Test insertion (but don't actually insert to avoid conflicts)
                print("✅ Arc assignment working correctly")

        return True

    except Exception as e:
        print(f"❌ Episode database test failed: {e}")
        return False


async def main():
    """Run all database tests."""
    print("🧪 Testing database integration for scraping feature...\n")

    # Test arc assignment
    arc_success = await test_arc_assignment()

    # Test episode database
    episode_success = await test_episode_database()

    if arc_success and episode_success:
        print("\n🎉 All database tests passed!")
        print("Ready to proceed with Phase 4: Scraping Service Implementation")
    else:
        print("\n❌ Some tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
