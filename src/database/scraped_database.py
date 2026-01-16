"""
Database manager for scraped One Piece episodes.

This module handles:
- Scraped episode CRUD operations
- Batch insert operations
- Arc assignment integration
- Episode existence checking
"""

from typing import List, Optional, Set, Dict
from supabase import create_client, Client
from loguru import logger
from postgrest.types import CountMethod

from ..config import config
from ..models import ScrapedEpisodeForDB, ScrapedEpisodeFromDB
from .arc_database import ArcDatabase


class ScrapedEpisodeDatabaseError(Exception):
    """Custom exception for scraped episode database errors."""
    pass


class ScrapedEpisodeDatabase:
    """
    Database client for managing scraped One Piece episodes in Supabase.

    This class provides methods to:
    - Insert new scraped episodes
    - Get existing episode IDs
    - Batch operations for efficiency
    - Arc assignment integration
    """

    def __init__(self):
        """Initialize the scraped episode database client."""
        self.client: Optional[Client] = None
        self.table_name = "scraped_episodes"
        self.arc_db = ArcDatabase()

    def _ensure_connected(self) -> Client:
        """
        Ensure database connection exists and return the client.

        Returns:
            Connected Supabase client

        Raises:
            ScrapedEpisodeDatabaseError: If not connected
        """
        if self.client is None:
            self.connect()

        if self.client is None:
            raise ScrapedEpisodeDatabaseError("Scraped episode database client is not connected")

        return self.client

    def connect(self) -> None:
        """
        Establish connection to Supabase.

        Raises:
            ScrapedEpisodeDatabaseError: If connection fails
        """
        try:
            self.client = create_client(
                config.supabase_url,
                config.supabase_key
            )
            # Also connect the arc database
            self.arc_db.connect()
            logger.info("Successfully connected to Supabase for scraped episodes")

        except Exception as e:
            error_msg = f"Failed to connect to Supabase for scraped episodes: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        # Supabase client doesn't need explicit cleanup
        pass

    def get_existing_episode_ids(self) -> Set[int]:
        """
        Get all episode IDs that already exist in the scraped episodes table.

        Returns:
            Set of existing episode IDs

        Raises:
            ScrapedEpisodeDatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            # Get all episode IDs without pagination limits
            all_episodes = []
            page_size = 1000
            offset = 0

            while True:
                response = client.table(self.table_name)\
                    .select("id")\
                    .range(offset, offset + page_size - 1)\
                    .execute()

                if not response.data:
                    break

                all_episodes.extend(response.data)

                # If we got less than page_size records, we've reached the end
                if len(response.data) < page_size:
                    break

                offset += page_size

            if all_episodes:
                existing_ids = {int(episode["id"]) for episode in all_episodes}  # type: ignore
                logger.info(f"Found {len(existing_ids)} existing scraped episodes")
                return existing_ids
            else:
                logger.info("No existing scraped episodes found")
                return set()

        except Exception as e:
            error_msg = f"Failed to get existing episode IDs: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def assign_arc_to_episode(self, episode: ScrapedEpisodeForDB) -> ScrapedEpisodeForDB:
        """
        Assign an arc to an episode based on its episode number.

        Args:
            episode: Episode to assign arc to

        Returns:
            Episode with arc_id assigned
        """
        if episode.arc_id is None:
            arc_id = self.arc_db.get_arc_id_for_episode(episode.id)
            if arc_id:
                episode.arc_id = arc_id
            else:
                # Fallback to Unknown Arc
                unknown_arc_id = self.arc_db.get_unknown_arc_id()
                episode.arc_id = unknown_arc_id
                logger.warning(f"Episode {episode.id} assigned to Unknown Arc")

        return episode

    def insert_episode(self, episode: ScrapedEpisodeForDB) -> bool:
        """
        Insert a single scraped episode into the database.

        Args:
            episode: Episode to insert

        Returns:
            True if successful, False otherwise

        Raises:
            ScrapedEpisodeDatabaseError: If insert fails
        """
        try:
            client = self._ensure_connected()

            # Ensure episode has arc assigned
            episode_with_arc = self.assign_arc_to_episode(episode)

            # Convert to dictionary for insertion
            episode_data = episode_with_arc.to_dict()

            response = client.table(self.table_name)\
                .insert(episode_data)\
                .execute()

            if response.data:
                logger.debug(f"Successfully inserted episode {episode.id}: {episode.title}")
                return True
            else:
                logger.error(f"Failed to insert episode {episode.id}: No data returned")
                return False

        except Exception as e:
            error_msg = f"Failed to insert episode {episode.id}: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def insert_episodes_batch(self, episodes: List[ScrapedEpisodeForDB], batch_size: int = 100) -> Dict[str, int]:
        """
        Insert multiple episodes in batches for efficiency.

        Args:
            episodes: List of episodes to insert
            batch_size: Number of episodes per batch

        Returns:
            Dictionary with statistics: {'inserted': count, 'failed': count}

        Raises:
            ScrapedEpisodeDatabaseError: If batch insert fails
        """
        stats = {'inserted': 0, 'failed': 0}

        try:
            client = self._ensure_connected()

            # Process episodes in batches
            for i in range(0, len(episodes), batch_size):
                batch = episodes[i:i + batch_size]

                # Assign arcs to all episodes in batch
                batch_with_arcs = [self.assign_arc_to_episode(ep) for ep in batch]

                # Convert to dictionaries
                batch_data = [ep.to_dict() for ep in batch_with_arcs]

                try:
                    response = client.table(self.table_name)\
                        .insert(batch_data)\
                        .execute()

                    if response.data:
                        batch_count = len(response.data)
                        stats['inserted'] += batch_count
                        logger.info(f"Inserted batch of {batch_count} episodes (episodes {batch[0].id}-{batch[-1].id})")
                    else:
                        stats['failed'] += len(batch)
                        logger.error("Failed to insert batch: No data returned")

                except Exception as e:
                    stats['failed'] += len(batch)
                    logger.error(f"Failed to insert batch {i//batch_size + 1}: {str(e)}")
                    continue

            logger.success(f"Batch insert complete: {stats['inserted']} inserted, {stats['failed']} failed")
            return stats

        except Exception as e:
            error_msg = f"Failed to execute batch insert: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def get_episodes_with_arcs(self, limit: Optional[int] = None, offset: int = 0) -> List[ScrapedEpisodeFromDB]:
        """
        Get scraped episodes with their arc information.

        Args:
            limit: Maximum number of episodes to return
            offset: Number of episodes to skip

        Returns:
            List of episodes with arc information
        """
        try:
            client = self._ensure_connected()

            query = client.table(self.table_name)\
                .select("*, arcs(id, name)")\
                .order("id")\
                .range(offset, offset + limit - 1 if limit else None)

            response = query.execute()

            if response.data:
                episodes = []
                for episode_data in response.data:
                    # Extract arc information
                    arc_info = episode_data.pop('arcs', None)
                    if arc_info:
                        episode_data['arc_name'] = arc_info.get('name')

                    episodes.append(ScrapedEpisodeFromDB(**episode_data))

                logger.info(f"Retrieved {len(episodes)} scraped episodes with arc info")
                return episodes
            else:
                return []

        except Exception as e:
            error_msg = f"Failed to get episodes with arcs: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def get_episode_count(self) -> int:
        """
        Get the total number of scraped episodes in the database.

        Returns:
            Number of episodes
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name)\
                .select("count", count=CountMethod.exact)\
                .execute()

            return response.count if response.count is not None else 0

        except Exception as e:
            error_msg = f"Failed to get episode count: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    def get_episodes_by_arc(self, arc_id: int) -> List[ScrapedEpisodeFromDB]:
        """
        Get all episodes for a specific arc.

        Args:
            arc_id: ID of the arc

        Returns:
            List of episodes in the arc
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name)\
                .select("*, arcs(id, name)")\
                .eq("arc_id", arc_id)\
                .order("id")\
                .execute()

            if response.data:
                episodes = []
                for episode_data in response.data:
                    # Extract arc information
                    arc_info = episode_data.pop('arcs', None)
                    if arc_info:
                        episode_data['arc_name'] = arc_info.get('name')

                    episodes.append(ScrapedEpisodeFromDB(**episode_data))

                return episodes
            else:
                return []

        except Exception as e:
            error_msg = f"Failed to get episodes for arc {arc_id}: {str(e)}"
            logger.error(error_msg)
            raise ScrapedEpisodeDatabaseError(error_msg) from e

    async def health_check(self) -> bool:
        """
        Check if scraped episode database connection is working.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            client = self._ensure_connected()

            # Try a simple query to test connection
            client.table(self.table_name).select("count", count=CountMethod.exact).execute()

            logger.success("Scraped episode database health check passed")
            return True

        except Exception as e:
            logger.error(f"Scraped episode database health check failed: {e}")
            return False
