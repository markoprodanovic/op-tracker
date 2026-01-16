#!/usr/bin/env python3
"""
Comprehensive test for the complete scraping workflow.
This tests the entire process end-to-end without inserting real data.
"""

from src.scraping.scraping_service import EpisodeScrapingService
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))


async def test_complete_workflow():
    """Test the complete scraping workflow."""
    print("🧪 Testing complete scraping workflow...")

    try:
        async with EpisodeScrapingService() as service:
            # Test Step 1: Scraping (use first 10 episodes for testing)
            print("\n1️⃣ Testing episode scraping...")
            scraped_data = await service._scrape_episodes()
            print(f"   ✅ Scraped {len(scraped_data)} episodes")

            # Test Step 2: Get existing episodes
            print("\n2️⃣ Testing existing episode lookup...")
            existing_ids = await service._get_existing_episodes()
            print(f"   ✅ Found {len(existing_ids)} existing episodes")

            # Test Step 3: Find new episodes (simulate with a few episodes)
            print("\n3️⃣ Testing new episode identification...")
            # Use first 5 episodes for testing
            test_episodes = scraped_data[:5]
            new_episodes = await service._find_new_episodes(test_episodes, existing_ids)
            print(f"   ✅ Identified {len(new_episodes)} new episodes from test set")

            # Test Step 4: Prepare episodes for database
            print("\n4️⃣ Testing episode preparation and arc assignment...")
            if new_episodes:
                episodes_for_db = await service._prepare_episodes_for_db(new_episodes)
                print(f"   ✅ Prepared {len(episodes_for_db)} episodes for database")

                # Show arc assignments for the test episodes
                for ep in episodes_for_db[:3]:  # Show first 3
                    # Get arc assignment
                    ep_with_arc = service.episode_db.assign_arc_to_episode(ep)
                    arc_info = service.arc_db.get_arc_by_id(ep_with_arc.arc_id) if ep_with_arc.arc_id else None
                    arc_name = arc_info.name if arc_info else "Unknown"
                    print(f"     Episode {ep.id}: {ep.title[:30]}... → {arc_name}")
            else:
                print("   ✅ No new episodes to prepare (database up to date)")

            # Test Step 5: Statistics
            print("\n5️⃣ Testing statistics and reporting...")
            service._update_final_stats({"inserted": len(new_episodes), "failed": 0})
            print("   ✅ Statistics updated successfully")

            # Show summary
            print("\n📊 Test Summary:")
            service.print_sync_summary()

        return True

    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_robustness():
    """Test error handling and edge cases."""
    print("\n🛡️  Testing service robustness...")

    try:
        async with EpisodeScrapingService() as service:
            # Test with invalid episode data
            print("\n🧪 Testing with invalid episode data...")
            invalid_episodes = [
                {"id": "invalid", "title": "", "airdate": None},  # Invalid ID
                {"title": "Missing ID", "airdate": None},  # Missing ID
            ]

            try:
                episodes_for_db = await service._prepare_episodes_for_db(invalid_episodes)
                print(f"   ✅ Handled invalid data gracefully - parsed {len(episodes_for_db)} valid episodes")
            except Exception as e:
                print(f"   ⚠️  Invalid data handling: {e}")

        return True

    except Exception as e:
        print(f"❌ Robustness test failed: {e}")
        return False


async def main():
    """Run all workflow tests."""
    print("🎬 Starting complete scraping workflow tests...\n")

    # Test complete workflow
    workflow_success = await test_complete_workflow()

    # Test robustness
    robustness_success = await test_service_robustness()

    if workflow_success and robustness_success:
        print("\n🎉 All workflow tests passed!")
        print("🚀 Ready to run the actual scraping service!")
        print("\nTo run the scraping service:")
        print("   python scraping_main.py")
    else:
        print("\n❌ Some workflow tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
