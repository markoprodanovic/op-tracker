from typing import List, Optional, Set
from supabase import create_client, Client
from loguru import logger

from ..config import config
from ..models import EpisodeForDB, EpisodeFromDB, DBEpisodeList


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class EpisodeDatabase:
    """
    Database client for managing One Piece episodes in Supabase.

    This class provides methods to:
    - Connect to Supabase
    - Insert new episodes
    - Query existing episodes
    - Update episode information
    - Get statistics about stored episodes
    """

    def __init__(self):
        """Initialize the database client with Supabase connection."""
        self.client: Optional[Client] = None
        self.table_name = "episodes"

    def _ensure_connected(self) -> Client:
        """
        Ensure database connection exists and return the client.

        Returns:
            Connected Supabase client

        Raises:
            DatabaseError: If not connected
        """
        if self.client is None:
            self.connect()

        if self.client is None:
            raise DatabaseError("Database client is not connected")

        return self.client

    def connect(self) -> None:
        """
        Establish connection to Supabase.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            self.client = create_client(
                config.supabase_url,
                config.supabase_key
            )
            logger.info("Successfully connected to Supabase database")

        except Exception as e:
            error_msg = f"Failed to connect to Supabase: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        # Supabase client doesn't need explicit cleanup
        pass

    async def health_check(self) -> bool:
        """
        Check if database connection is working.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            client = self._ensure_connected()

            # Try a simple query to test connection
            client.table(self.table_name).select("count", count="exact").execute()  # type: ignore

            logger.success("Database health check passed")
            return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_existing_episode_ids(self) -> Set[int]:
        """
        Get all episode IDs that already exist in the database.

        Uses pagination to handle large result sets.

        Returns:
            Set of episode IDs currently in the database

        Raises:
            DatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            logger.info("Fetching existing episode IDs from database")

            all_ids = set()
            page_size = 1000
            start = 0

            while True:
                # Query with pagination
                response = client.table(self.table_name).select("id").range(start, start + page_size - 1).execute()

                if not response.data:
                    break

                # Extract IDs from this page
                page_ids = {row["id"] for row in response.data}
                all_ids.update(page_ids)

                # If we got fewer than page_size results, we're done
                if len(response.data) < page_size:
                    break

                start += page_size

            logger.info(f"Found {len(all_ids)} existing episodes in database")
            return all_ids

        except Exception as e:
            error_msg = f"Failed to fetch existing episode IDs: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def get_all_episodes(self) -> DBEpisodeList:
        """
        Retrieve all episodes from the database.

        Uses pagination to handle large result sets.

        Returns:
            List of all episodes from database

        Raises:
            DatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            logger.info("Fetching all episodes from database")

            all_episodes = []
            page_size = 1000
            start = 0

            while True:
                # Query with pagination, ordered by ID
                response = client.table(self.table_name).select(
                    "*").order("id").range(start, start + page_size - 1).execute()

                if not response.data:
                    break

                # Convert to our model objects
                for row in response.data:
                    try:
                        episode = EpisodeFromDB(**row)
                        all_episodes.append(episode)
                    except Exception as e:
                        logger.warning(f"Failed to parse episode {row.get('id', 'unknown')}: {e}")
                        continue

                # If we got fewer than page_size results, we're done
                if len(response.data) < page_size:
                    break

                start += page_size

            logger.success(f"Retrieved {len(all_episodes)} episodes from database")
            return all_episodes

        except Exception as e:
            error_msg = f"Failed to fetch episodes from database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def get_episode_by_id(self, episode_id: int) -> Optional[EpisodeFromDB]:
        """
        Get a specific episode by ID.

        Args:
            episode_id: ID of episode to retrieve

        Returns:
            Episode if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name).select("*").eq("id", episode_id).execute()

            if not response.data:
                return None

            episode_data = response.data[0]
            episode = EpisodeFromDB(**episode_data)

            logger.debug(f"Retrieved episode {episode_id}: {episode.title}")
            return episode

        except Exception as e:
            error_msg = f"Failed to fetch episode {episode_id}: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def insert_episodes(self, episodes: List[EpisodeForDB]) -> int:
        """
        Insert multiple episodes into the database.

        Uses upsert (insert or update) to handle duplicates gracefully.

        Args:
            episodes: List of episodes to insert

        Returns:
            Number of episodes successfully inserted/updated

        Raises:
            DatabaseError: If insertion fails
        """
        if not episodes:
            logger.info("No episodes to insert")
            return 0

        try:
            client = self._ensure_connected()

            logger.info(f"Inserting {len(episodes)} episodes into database")

            # Convert episodes to dictionaries
            episode_dicts = [episode.to_dict() for episode in episodes]

            # Use upsert to handle duplicates (update if exists, insert if new)
            response = client.table(self.table_name).upsert(
                episode_dicts,
                on_conflict="id"  # Use ID as the conflict resolution key
            ).execute()

            inserted_count = len(response.data) if response.data else len(episodes)

            logger.success(f"Successfully inserted/updated {inserted_count} episodes")
            return inserted_count

        except Exception as e:
            error_msg = f"Failed to insert episodes: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def insert_episode(self, episode: EpisodeForDB) -> bool:
        """
        Insert a single episode into the database.

        Args:
            episode: Episode to insert

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.insert_episodes([episode])
            return result > 0
        except DatabaseError:
            return False

    def get_database_stats(self) -> dict:
        """
        Get statistics about the episodes in the database.

        Returns:
            Dictionary with database statistics

        Raises:
            DatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            logger.info("Calculating database statistics")

            # Get total count
            count_response = client.table(self.table_name).select("*", count="exact").execute()  # type: ignore
            total_episodes = count_response.count

            if total_episodes == 0:
                return {
                    "total_episodes": 0,
                    "earliest_episode": None,
                    "latest_episode": None,
                    "earliest_release_date": None,
                    "latest_release_date": None,
                    "unique_sagas": 0,
                    "unique_arcs": 0
                }

            # Get min/max episode IDs efficiently
            min_response = client.table(self.table_name).select("id").order("id").limit(1).execute()
            max_response = client.table(self.table_name).select("id").order("id", desc=True).limit(1).execute()

            min_episode_id = min_response.data[0]["id"] if min_response.data else None
            max_episode_id = max_response.data[0]["id"] if max_response.data else None

            # Get release dates and metadata efficiently with pagination
            all_release_dates = []
            all_sagas = set()
            all_arcs = set()

            page_size = 1000
            start = 0

            while True:
                data_response = client.table(self.table_name).select(
                    "release_date, saga_title, arc_title"
                ).range(start, start + page_size - 1).execute()

                if not data_response.data:
                    break

                for row in data_response.data:
                    if row["release_date"]:
                        all_release_dates.append(row["release_date"])
                    if row["saga_title"]:
                        all_sagas.add(row["saga_title"])
                    if row["arc_title"]:
                        all_arcs.add(row["arc_title"])

                if len(data_response.data) < page_size:
                    break

                start += page_size

            stats = {
                "total_episodes": total_episodes,
                "earliest_episode": min_episode_id,
                "latest_episode": max_episode_id,
                "earliest_release_date": min(all_release_dates) if all_release_dates else None,
                "latest_release_date": max(all_release_dates) if all_release_dates else None,
                "unique_sagas": len(all_sagas),
                "unique_arcs": len(all_arcs)
            }

            logger.success("Database statistics calculated successfully")
            return stats

        except Exception as e:
            error_msg = f"Failed to calculate database statistics: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def delete_episode(self, episode_id: int) -> bool:
        """
        Delete an episode from the database.

        Args:
            episode_id: ID of episode to delete

        Returns:
            True if episode was deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name).delete().eq("id", episode_id).execute()

            deleted = len(response.data) > 0

            if deleted:
                logger.info(f"Deleted episode {episode_id}")
            else:
                logger.info(f"Episode {episode_id} not found for deletion")

            return deleted

        except Exception as e:
            error_msg = f"Failed to delete episode {episode_id}: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg) from e


# Convenience functions for quick database operations
def get_existing_episode_ids() -> Set[int]:
    """Get all existing episode IDs from database."""
    with EpisodeDatabase() as db:
        return db.get_existing_episode_ids()


def insert_episodes(episodes: List[EpisodeForDB]) -> int:
    """Insert multiple episodes into database."""
    with EpisodeDatabase() as db:
        return db.insert_episodes(episodes)


def get_database_stats() -> dict:
    """Get database statistics."""
    with EpisodeDatabase() as db:
        return db.get_database_stats()
