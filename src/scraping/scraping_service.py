"""
Main scraping service for One Piece episodes.

This module orchestrates the entire scraping process:
- Scrapes episodes from animefillerlist.com
- Compares with existing database episodes
- Assigns arcs to new episodes
- Inserts new episodes in batches
- Provides comprehensive logging and statistics
"""

from typing import List, Dict, Set, Any
from datetime import datetime
from loguru import logger

from .scraper import scrape_one_piece_episodes
from ..database.scraped_database import ScrapedEpisodeDatabase
from ..database.arc_database import ArcDatabase
from ..models import ScrapedEpisode, ScrapedEpisodeForDB


class EpisodeScrapingError(Exception):
    """Custom exception for scraping service errors."""
    pass


class EpisodeScrapingService:
    """
    Main service class for scraping and storing One Piece episodes.

    This class orchestrates:
    1. Web scraping from animefillerlist.com
    2. Comparison with existing database episodes
    3. Arc assignment for new episodes
    4. Batch insertion of new episodes
    5. Comprehensive statistics and reporting
    """

    def __init__(self):
        """Initialize the scraping service."""
        self.episode_db = ScrapedEpisodeDatabase()
        self.arc_db = ArcDatabase()

        # Statistics tracking
        self.stats = {
            "sync_start_time": None,
            "sync_end_time": None,
            "episodes_scraped": 0,
            "episodes_parsed": 0,
            "existing_episodes_in_db": 0,
            "new_episodes_found": 0,
            "episodes_inserted": 0,
            "episodes_failed": 0,
            "sync_duration_seconds": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.episode_db.connect()
        self.arc_db.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # No cleanup needed for Supabase clients
        pass

    async def scrape_and_sync_episodes(self) -> Dict[str, Any]:
        """
        Main method to scrape episodes and sync with database.

        Returns:
            Dictionary with sync statistics

        Raises:
            EpisodeScrapingError: If sync process fails
        """
        logger.info("🚀 Starting One Piece episode scraping and sync process")
        self.stats["sync_start_time"] = datetime.now()

        try:
            # Step 1: Scrape episodes from website
            scraped_episodes = await self._scrape_episodes()

            # Step 2: Get existing episodes from database
            existing_episode_ids = await self._get_existing_episodes()

            # Step 3: Find new episodes to insert
            new_episodes = await self._find_new_episodes(scraped_episodes, existing_episode_ids)

            # Step 4: Convert and assign arcs to new episodes
            episodes_for_db = await self._prepare_episodes_for_db(new_episodes)

            # Step 5: Insert new episodes in batches
            insert_stats = await self._insert_episodes_batch(episodes_for_db)

            # Step 6: Update final statistics
            self._update_final_stats(insert_stats)

            logger.success("✅ Episode scraping and sync completed successfully")
            return self.stats

        except Exception as e:
            error_msg = f"Episode scraping and sync failed: {str(e)}"
            logger.error(error_msg)
            raise EpisodeScrapingError(error_msg) from e

        finally:
            self.stats["sync_end_time"] = datetime.now()
            if self.stats["sync_start_time"]:
                duration = self.stats["sync_end_time"] - self.stats["sync_start_time"]
                self.stats["sync_duration_seconds"] = duration.total_seconds()

    async def _scrape_episodes(self) -> List[Dict[str, Any]]:
        """Scrape episodes from animefillerlist.com."""
        logger.info("🌐 Scraping episodes from animefillerlist.com...")

        try:
            scraped_data = await scrape_one_piece_episodes()
            self.stats["episodes_scraped"] = len(scraped_data)

            logger.info(f"📺 Successfully scraped {len(scraped_data)} episodes from website")
            return scraped_data

        except Exception as e:
            error_msg = f"Failed to scrape episodes: {str(e)}"
            logger.error(error_msg)
            raise EpisodeScrapingError(error_msg) from e

    async def _get_existing_episodes(self) -> Set[int]:
        """Get existing episode IDs from database."""
        logger.info("🔍 Checking existing episodes in database...")

        try:
            existing_ids = self.episode_db.get_existing_episode_ids()
            self.stats["existing_episodes_in_db"] = len(existing_ids)

            logger.info(f"💾 Found {len(existing_ids)} existing episodes in database")
            return existing_ids

        except Exception as e:
            error_msg = f"Failed to get existing episodes: {str(e)}"
            logger.error(error_msg)
            raise EpisodeScrapingError(error_msg) from e

    async def _find_new_episodes(
        self,
        scraped_episodes: List[Dict[str, Any]],
        existing_ids: Set[int]
    ) -> List[Dict[str, Any]]:
        """Find episodes that don't exist in database yet."""
        logger.info("🆕 Identifying new episodes to insert...")

        new_episodes = []
        for episode_data in scraped_episodes:
            if episode_data["id"] not in existing_ids:
                new_episodes.append(episode_data)

        self.stats["new_episodes_found"] = len(new_episodes)

        if new_episodes:
            logger.info(f"📈 Found {len(new_episodes)} new episodes to insert")
            logger.info(f"📊 Episode range: {new_episodes[0]['id']} to {new_episodes[-1]['id']}")
        else:
            logger.info("✅ No new episodes found - database is up to date!")

        return new_episodes

    async def _prepare_episodes_for_db(self, new_episodes: List[Dict[str, Any]]) -> List[ScrapedEpisodeForDB]:
        """Convert scraped episodes to database-ready format with arc assignments."""
        logger.info("🎯 Preparing episodes for database insertion...")

        episodes_for_db = []
        parsed_count = 0
        failed_count = 0

        for episode_data in new_episodes:
            try:
                # Parse the scraped episode
                scraped_episode = ScrapedEpisode(**episode_data)

                # Convert to database format
                db_episode = ScrapedEpisodeForDB.from_scraped_episode(scraped_episode)

                # Arc assignment will be handled by the database layer
                episodes_for_db.append(db_episode)
                parsed_count += 1

            except Exception as e:
                logger.warning(f"Failed to parse episode {episode_data.get('id', 'unknown')}: {e}")
                failed_count += 1
                continue

        self.stats["episodes_parsed"] = parsed_count

        logger.info(f"✅ Prepared {parsed_count} episodes for insertion ({failed_count} failed parsing)")
        return episodes_for_db

    async def _insert_episodes_batch(self, episodes: List[ScrapedEpisodeForDB]) -> Dict[str, int]:
        """Insert episodes in batches."""
        if not episodes:
            return {"inserted": 0, "failed": 0}

        logger.info(f"💾 Inserting {len(episodes)} episodes into database...")

        try:
            insert_stats = self.episode_db.insert_episodes_batch(episodes, batch_size=50)

            logger.success(
                f"✅ Database insertion complete: {insert_stats['inserted']} inserted, {insert_stats['failed']} failed")
            return insert_stats

        except Exception as e:
            error_msg = f"Failed to insert episodes: {str(e)}"
            logger.error(error_msg)
            raise EpisodeScrapingError(error_msg) from e

    def _update_final_stats(self, insert_stats: Dict[str, int]) -> None:
        """Update final statistics."""
        self.stats["episodes_inserted"] = insert_stats["inserted"]
        self.stats["episodes_failed"] = insert_stats["failed"]

    def print_sync_summary(self) -> None:
        """Print a comprehensive summary of the sync process."""
        print("\n" + "="*60)
        print("🏴‍☠️ ONE PIECE EPISODE SYNC SUMMARY")
        print("="*60)

        if self.stats["sync_start_time"]:
            print(f"⏰ Sync Started: {self.stats['sync_start_time'].strftime('%Y-%m-%d %H:%M:%S')}")

        if self.stats["sync_end_time"]:
            print(f"⏰ Sync Ended: {self.stats['sync_end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duration: {self.stats['sync_duration_seconds']:.1f} seconds")

        print("\n📊 STATISTICS:")
        print(f"  🌐 Episodes scraped from website: {self.stats['episodes_scraped']}")
        print(f"  💾 Existing episodes in database: {self.stats['existing_episodes_in_db']}")
        print(f"  🆕 New episodes found: {self.stats['new_episodes_found']}")
        print(f"  ✅ Episodes successfully inserted: {self.stats['episodes_inserted']}")
        print(f"  ❌ Episodes failed to insert: {self.stats['episodes_failed']}")

        if self.stats['new_episodes_found'] > 0:
            success_rate = (self.stats['episodes_inserted'] / self.stats['new_episodes_found']) * 100
            print(f"  📈 Success rate: {success_rate:.1f}%")

        print("="*60)


# Convenience function for simple usage
async def sync_one_piece_episodes() -> Dict[str, Any]:
    """
    Convenience function to sync One Piece episodes.

    Returns:
        Dictionary with sync statistics
    """
    async with EpisodeScrapingService() as service:
        stats = await service.scrape_and_sync_episodes()
        service.print_sync_summary()
        return stats
