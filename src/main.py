"""
Main application for the One Piece episode tracker.

This module contains the core business logic that:
- Fetches episodes from the One Piece API
- Compares with existing database episodes
- Inserts new episodes
- Updates existing episodes if needed
- Provides reporting and statistics
"""

import asyncio
from typing import List, Set
from datetime import datetime, timezone
from loguru import logger

from src.config import config
from src.api_client import OnePieceAPIClient, OnePieceAPIError
from src.database import EpisodeDatabase, DatabaseError
from src.models import EpisodeForDB, APIEpisodeList


class EpisodeTrackerError(Exception):
    """Custom exception for episode tracker errors."""
    pass


class EpisodeTracker:
    """
    Main application class for tracking One Piece episodes.

    This class orchestrates the entire sync process:
    1. Fetch episodes from API
    2. Check which episodes are new
    3. Insert/update episodes in database
    4. Provide sync statistics and reporting
    """

    def __init__(self):
        """Initialize the episode tracker."""
        self.api_client = OnePieceAPIClient()
        self.database = EpisodeDatabase()

        # Statistics tracking
        self.sync_stats = {
            "sync_start_time": None,
            "sync_end_time": None,
            "api_episodes_fetched": 0,
            "api_episodes_parsed": 0,
            "existing_episodes_in_db": 0,
            "new_episodes_found": 0,
            "episodes_inserted": 0,
            "episodes_updated": 0,
            "episodes_skipped": 0,
            "errors_encountered": 0
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.api_client.__aexit__(exc_type, exc_val, exc_tb)

    async def health_check(self) -> dict:
        """
        Check the health of both API and database connections.

        Returns:
            Dictionary with health status of each component
        """
        logger.info("Performing health checks...")

        health_status = {
            "api_healthy": False,
            "database_healthy": False,
            "overall_healthy": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Test API connection
            health_status["api_healthy"] = await self.api_client.health_check()

            # Test database connection
            with self.database:
                health_status["database_healthy"] = await self.database.health_check()

            # Overall health
            health_status["overall_healthy"] = (
                health_status["api_healthy"] and health_status["database_healthy"]
            )

            if health_status["overall_healthy"]:
                logger.success("All systems healthy!")
            else:
                logger.warning("Some systems are not healthy")

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["error"] = str(e)

        return health_status

    def _filter_valid_episodes(self, api_episodes: APIEpisodeList) -> List[EpisodeForDB]:
        """
        Filter and convert API episodes to database format.

        Now handles missing arc/saga data by using placeholder values
        instead of skipping episodes entirely.

        Args:
            api_episodes: Raw episodes from API

        Returns:
            List of episodes ready for database insertion
        """
        valid_episodes = []

        for api_episode in api_episodes:
            try:
                # Convert to database format (now handles missing arc/saga gracefully)
                db_episode = EpisodeForDB.from_api_episode(api_episode)
                valid_episodes.append(db_episode)

                # Log if we used placeholder data
                if db_episode.arc_title == "Unknown Arc" or db_episode.saga_title == "Unknown Saga":
                    logger.info(
                        f"Episode {api_episode.id} has missing metadata - "
                        f"using placeholders (Arc: {db_episode.arc_title}, Saga: {db_episode.saga_title})"
                    )

            except Exception as e:
                # Should be rare now, but still handle unexpected parsing errors
                logger.warning(f"Skipping episode {api_episode.id} due to parsing error: {e}")
                self.sync_stats["episodes_skipped"] += 1
                continue

        logger.info(f"Processed {len(valid_episodes)} episodes from {len(api_episodes)} API episodes")
        return valid_episodes

    def _identify_new_episodes(self, db_episodes: List[EpisodeForDB], existing_ids: Set[int]) -> List[EpisodeForDB]:
        """
        Identify which episodes are new (not in database).

        Args:
            db_episodes: All valid episodes from API
            existing_ids: Set of episode IDs already in database

        Returns:
            List of new episodes to insert
        """
        new_episodes = [ep for ep in db_episodes if ep.id not in existing_ids]

        if new_episodes:
            new_ids = [ep.id for ep in new_episodes]
            logger.info(f"Found {len(new_episodes)} new episodes: {new_ids}")
        else:
            logger.info("No new episodes found")

        return new_episodes

    async def sync_episodes(self, force_update: bool = False) -> dict:
        """
        Main sync method - fetch episodes from API and update database.

        Args:
            force_update: If True, update all episodes even if they exist

        Returns:
            Dictionary with sync statistics and results
        """
        logger.info("Starting episode sync process...")
        self.sync_stats["sync_start_time"] = datetime.now(timezone.utc)

        try:
            # Step 1: Fetch episodes from API
            logger.info("Step 1: Fetching episodes from One Piece API...")
            async with self.api_client:
                api_episodes = await self.api_client.fetch_all_episodes()

            self.sync_stats["api_episodes_fetched"] = len(api_episodes)
            logger.success(f"Fetched {len(api_episodes)} episodes from API")

            # Step 2: Filter and convert episodes
            logger.info("Step 2: Processing and validating episodes...")
            valid_episodes = self._filter_valid_episodes(api_episodes)
            self.sync_stats["api_episodes_parsed"] = len(valid_episodes)

            if not valid_episodes:
                logger.warning("No valid episodes to process")
                return self._finalize_sync_stats()

            # Step 3: Check existing episodes in database
            logger.info("Step 3: Checking existing episodes in database...")
            with self.database:
                existing_ids = self.database.get_existing_episode_ids()

            self.sync_stats["existing_episodes_in_db"] = len(existing_ids)
            logger.info(f"Found {len(existing_ids)} existing episodes in database")

            # Step 4: Determine what to insert/update
            if force_update:
                logger.info("Force update enabled - will update all episodes")
                episodes_to_process = valid_episodes
                self.sync_stats["episodes_updated"] = len(valid_episodes)
            else:
                episodes_to_process = self._identify_new_episodes(valid_episodes, existing_ids)
                self.sync_stats["new_episodes_found"] = len(episodes_to_process)
                self.sync_stats["episodes_inserted"] = len(episodes_to_process)

            # Step 5: Insert/update episodes in database
            if episodes_to_process:
                logger.info(f"Step 5: Inserting/updating {len(episodes_to_process)} episodes...")
                with self.database:
                    inserted_count = self.database.insert_episodes(episodes_to_process)

                logger.success(f"Successfully processed {inserted_count} episodes")

                # Update stats with actual inserted count
                if force_update:
                    self.sync_stats["episodes_updated"] = inserted_count
                else:
                    self.sync_stats["episodes_inserted"] = inserted_count
            else:
                logger.info("No episodes to process - database is up to date")

            # Step 6: Get final database statistics
            logger.info("Step 6: Calculating final statistics...")
            with self.database:
                db_stats = self.database.get_database_stats()

            sync_result = self._finalize_sync_stats()
            sync_result["database_stats"] = db_stats

            logger.success("Episode sync completed successfully!")
            return sync_result

        except OnePieceAPIError as e:
            error_msg = f"API error during sync: {e}"
            logger.error(error_msg)
            self.sync_stats["errors_encountered"] += 1
            raise EpisodeTrackerError(error_msg) from e

        except DatabaseError as e:
            error_msg = f"Database error during sync: {e}"
            logger.error(error_msg)
            self.sync_stats["errors_encountered"] += 1
            raise EpisodeTrackerError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error during sync: {e}"
            logger.error(error_msg)
            self.sync_stats["errors_encountered"] += 1
            raise EpisodeTrackerError(error_msg) from e

    def _finalize_sync_stats(self) -> dict:
        """Finalize sync statistics and return them."""
        self.sync_stats["sync_end_time"] = datetime.now(timezone.utc)

        # Calculate duration
        if self.sync_stats["sync_start_time"]:
            duration = self.sync_stats["sync_end_time"] - self.sync_stats["sync_start_time"]
            self.sync_stats["sync_duration_seconds"] = duration.total_seconds()

        return self.sync_stats.copy()

    async def get_sync_report(self) -> dict:
        """
        Generate a comprehensive sync report.

        Returns:
            Dictionary with current database state and recommendations
        """
        logger.info("Generating sync report...")

        try:
            # Get current database stats
            with self.database:
                db_stats = self.database.get_database_stats()

            # Get API stats for comparison
            async with self.api_client:
                api_episodes = await self.api_client.fetch_all_episodes()

            api_episodes_count = len(api_episodes)
            valid_api_episodes = self._filter_valid_episodes(api_episodes)
            valid_api_count = len(valid_api_episodes)

            # Calculate differences
            episodes_missing = valid_api_count - db_stats["total_episodes"]

            report = {
                "report_timestamp": datetime.now(timezone.utc).isoformat(),
                "api_status": {
                    "total_episodes_available": api_episodes_count,
                    "valid_episodes_available": valid_api_count,
                    "invalid_episodes": api_episodes_count - valid_api_count
                },
                "database_status": db_stats,
                "sync_analysis": {
                    "episodes_missing_from_db": max(0, episodes_missing),
                    "database_up_to_date": episodes_missing <= 0,
                    "sync_recommended": episodes_missing > 0
                },
                "last_sync_stats": self.sync_stats
            }

            logger.success("Sync report generated successfully")
            return report

        except Exception as e:
            logger.error(f"Failed to generate sync report: {e}")
            raise EpisodeTrackerError(f"Report generation failed: {e}") from e


# Convenience functions for direct use
async def sync_episodes(force_update: bool = False) -> dict:
    """
    Convenience function to sync episodes.

    Args:
        force_update: Whether to update all episodes

    Returns:
        Sync statistics
    """
    async with EpisodeTracker() as tracker:
        return await tracker.sync_episodes(force_update=force_update)


async def get_health_status() -> dict:
    """
    Convenience function to check system health.

    Returns:
        Health status of API and database
    """
    async with EpisodeTracker() as tracker:
        return await tracker.health_check()


async def generate_report() -> dict:
    """
    Convenience function to generate sync report.

    Returns:
        Comprehensive sync report
    """
    async with EpisodeTracker() as tracker:
        return await tracker.get_sync_report()


# Main CLI entry point
async def main():
    """
    Main entry point for running the episode tracker.

    This function can be called directly or used as a CLI.
    """
    logger.info("One Piece Episode Tracker Starting...")

    try:
        # Setup logging level from config
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=''),
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
            level=config.log_level
        )

        # Perform health check
        logger.info("Performing system health check...")
        health = await get_health_status()

        if not health["overall_healthy"]:
            logger.error("System health check failed!")
            logger.error(f"API healthy: {health['api_healthy']}")
            logger.error(f"Database healthy: {health['database_healthy']}")
            return False

        logger.success("System health check passed!")

        # Run sync
        logger.info("Starting episode sync...")
        sync_result = await sync_episodes()

        # Print summary
        print("\n" + "="*60)
        print("SYNC SUMMARY")
        print("="*60)
        print(f"Episodes fetched from API: {sync_result['api_episodes_fetched']}")
        print(f"Valid episodes parsed: {sync_result['api_episodes_parsed']}")
        print(f"Episodes already in DB: {sync_result['existing_episodes_in_db']}")
        print(f"New episodes found: {sync_result['new_episodes_found']}")
        print(f"Episodes inserted: {sync_result['episodes_inserted']}")
        print(f"Episodes skipped: {sync_result['episodes_skipped']}")
        print(f"Sync duration: {sync_result.get('sync_duration_seconds', 0):.2f} seconds")

        if 'database_stats' in sync_result:
            db_stats = sync_result['database_stats']
            print(f"\nDatabase now contains:")
            print(f"- Total episodes: {db_stats['total_episodes']}")
            print(f"- Episode range: {db_stats['earliest_episode']} to {db_stats['latest_episode']}")
            print(f"- Date range: {db_stats['earliest_release_date']} to {db_stats['latest_release_date']}")
            print(f"- Unique sagas: {db_stats['unique_sagas']}")
            print(f"- Unique arcs: {db_stats['unique_arcs']}")

        print("="*60)
        logger.success("Episode sync completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Episode tracker failed: {e}")
        return False


if __name__ == "__main__":
    # Run the main function
    success = asyncio.run(main())
    exit(0 if success else 1)
