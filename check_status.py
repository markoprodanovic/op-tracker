#!/usr/bin/env python3
"""
Status check script for monitoring.
Shows database state and recent activity for both API and scraped data.
"""

import asyncio
from datetime import datetime
from src.database.database import EpisodeDatabase
from src.database.scraped_database import ScrapedEpisodeDatabase
from src.database.arc_database import ArcDatabase


async def check_api_episodes():
    """Check status of API-based episodes."""
    print("\n📡 API Episodes (Original System)")
    print("-" * 30)

    try:
        with EpisodeDatabase() as db:
            existing_ids = db.get_existing_episode_ids()
            print(f"  Episodes in database: {len(existing_ids)}")

            if existing_ids:
                min_episode = min(existing_ids)
                max_episode = max(existing_ids)
                print(f"  Episode range: {min_episode} - {max_episode}")

            health = await db.health_check()
            print(f"  Database health: {'✅ Good' if health else '❌ Issues'}")

    except Exception as e:
        print(f"  ❌ Error checking API episodes: {e}")


async def check_scraped_episodes():
    """Check status of scraped episodes."""
    print("\n🌐 Scraped Episodes (New System)")
    print("-" * 30)

    try:
        with ScrapedEpisodeDatabase() as db:
            count = db.get_episode_count()
            print(f"  Episodes in database: {count}")

            if count > 0:
                # Get some sample episodes to show range
                sample_episodes = db.get_episodes_with_arcs(limit=1, offset=0)
                last_episodes = db.get_episodes_with_arcs(limit=1, offset=count-1)

                if sample_episodes and last_episodes:
                    first_ep = sample_episodes[0].id
                    last_ep = last_episodes[0].id
                    print(f"  Episode range: {first_ep} - {last_ep}")

            health = await db.health_check()
            print(f"  Database health: {'✅ Good' if health else '❌ Issues'}")

    except Exception as e:
        print(f"  ❌ Error checking scraped episodes: {e}")


async def check_arcs():
    """Check status of arc system."""
    print("\n🏴‍☠️ Story Arcs")
    print("-" * 30)

    try:
        with ArcDatabase() as db:
            arcs = db.get_all_arcs()
            print(f"  Total arcs: {len(arcs)}")

            if arcs:
                print("  Arc coverage:")
                for arc in arcs[:5]:  # Show first 5 arcs
                    if arc.name != "Unknown Arc":
                        print(f"    {arc.name}: Episodes {arc.start_episode}-{arc.end_episode}")

                if len(arcs) > 5:
                    print(f"    ... and {len(arcs) - 5} more arcs")

            health = await db.health_check()
            print(f"  Database health: {'✅ Good' if health else '❌ Issues'}")

    except Exception as e:
        print(f"  ❌ Error checking arcs: {e}")


async def main():
    print("One Piece Episode Tracker - Status Check")
    print("=" * 50)
    print(f"🕐 Status as of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check all systems
    await check_api_episodes()
    await check_scraped_episodes()
    await check_arcs()

    print("\n" + "=" * 50)
    print("Status check complete!")


if __name__ == "__main__":
    asyncio.run(main())
