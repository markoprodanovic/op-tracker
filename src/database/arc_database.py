"""
Database manager for One Piece story arcs.

This module handles:
- Arc CRUD operations
- Episode range lookups
- Arc assignment logic
"""

from typing import List, Optional
from supabase import create_client, Client
from postgrest.types import CountMethod
from loguru import logger

from ..config import config
from ..models import Arc


class ArcDatabaseError(Exception):
    """Custom exception for arc database-related errors."""
    pass


class ArcDatabase:
    """
    Database client for managing One Piece story arcs in Supabase.

    This class provides methods to:
    - Get all arcs
    - Find arc by episode number
    - Basic arc CRUD operations
    """

    def __init__(self):
        """Initialize the arc database client."""
        self.client: Optional[Client] = None
        self.table_name = "arcs"

    def _ensure_connected(self) -> Client:
        """
        Ensure database connection exists and return the client.

        Returns:
            Connected Supabase client

        Raises:
            ArcDatabaseError: If not connected
        """
        if self.client is None:
            self.connect()

        if self.client is None:
            raise ArcDatabaseError("Arc database client is not connected")

        return self.client

    def connect(self) -> None:
        """
        Establish connection to Supabase.

        Raises:
            ArcDatabaseError: If connection fails
        """
        try:
            self.client = create_client(
                config.supabase_url,
                config.supabase_key
            )
            logger.info("Successfully connected to Supabase for arc management")

        except Exception as e:
            error_msg = f"Failed to connect to Supabase for arcs: {str(e)}"
            logger.error(error_msg)
            raise ArcDatabaseError(error_msg) from e

    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        # Supabase client doesn't need explicit cleanup
        pass

    def get_all_arcs(self) -> List[Arc]:
        """
        Get all story arcs from the database.

        Returns:
            List of Arc objects ordered by start_episode

        Raises:
            ArcDatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name)\
                .select("*")\
                .order("start_episode")\
                .execute()

            if response.data:
                arcs = [Arc(**arc_data) for arc_data in response.data]
                logger.info(f"Retrieved {len(arcs)} arcs from database")
                return arcs
            else:
                logger.warning("No arcs found in database")
                return []

        except Exception as e:
            error_msg = f"Failed to get arcs: {str(e)}"
            logger.error(error_msg)
            raise ArcDatabaseError(error_msg) from e

    def get_arc_for_episode(self, episode_number: int) -> Optional[Arc]:
        """
        Find the arc that contains a specific episode number.

        Args:
            episode_number: Episode number to find arc for

        Returns:
            Arc object if found, None otherwise

        Raises:
            ArcDatabaseError: If query fails
        """
        try:
            client = self._ensure_connected()

            # Query for arc that contains this episode number
            response = client.table(self.table_name)\
                .select("*")\
                .gte("end_episode", episode_number)\
                .lte("start_episode", episode_number)\
                .neq("name", "Unknown Arc")\
                .order("start_episode")\
                .limit(1)\
                .execute()

            if response.data and len(response.data) > 0:
                arc = Arc(**response.data[0])
                logger.debug(f"Episode {episode_number} belongs to arc: {arc.name}")
                return arc
            else:
                # Try to get the "Unknown Arc" as fallback
                unknown_response = client.table(self.table_name)\
                    .select("*")\
                    .eq("name", "Unknown Arc")\
                    .limit(1)\
                    .execute()

                if unknown_response.data and len(unknown_response.data) > 0:
                    arc = Arc(**unknown_response.data[0])
                    logger.debug(f"Episode {episode_number} assigned to Unknown Arc")
                    return arc
                else:
                    logger.warning(f"No arc found for episode {episode_number} and no Unknown Arc available")
                    return None

        except Exception as e:
            error_msg = f"Failed to find arc for episode {episode_number}: {str(e)}"
            logger.error(error_msg)
            raise ArcDatabaseError(error_msg) from e

    def get_arc_id_for_episode(self, episode_number: int) -> Optional[int]:
        """
        Get the arc ID for a specific episode number.

        This is a convenience method that just returns the ID.

        Args:
            episode_number: Episode number to find arc for

        Returns:
            Arc ID if found, None otherwise
        """
        arc = self.get_arc_for_episode(episode_number)
        return arc.id if arc else None

    def get_unknown_arc_id(self) -> Optional[int]:
        """
        Get the ID of the "Unknown Arc".

        Returns:
            Unknown Arc ID if found, None otherwise
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name)\
                .select("id")\
                .eq("name", "Unknown Arc")\
                .limit(1)\
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0]["id"]
            else:
                logger.warning("Unknown Arc not found in database")
                return None

        except Exception as e:
            error_msg = f"Failed to get Unknown Arc ID: {str(e)}"
            logger.error(error_msg)
            raise ArcDatabaseError(error_msg) from e

    def get_arc_by_id(self, arc_id: int) -> Optional[Arc]:
        """
        Get a specific arc by its ID.

        Args:
            arc_id: Arc ID to retrieve

        Returns:
            Arc object if found, None otherwise
        """
        try:
            client = self._ensure_connected()

            response = client.table(self.table_name)\
                .select("*")\
                .eq("id", arc_id)\
                .limit(1)\
                .execute()

            if response.data and len(response.data) > 0:
                return Arc(**response.data[0])
            else:
                logger.warning(f"Arc with ID {arc_id} not found")
                return None

        except Exception as e:
            error_msg = f"Failed to get arc {arc_id}: {str(e)}"
            logger.error(error_msg)
            raise ArcDatabaseError(error_msg) from e

    async def health_check(self) -> bool:
        """
        Check if arc database connection is working.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            client = self._ensure_connected()
            # Try a simple query to test connection
            client.table(self.table_name).select("count", count=CountMethod.exact).execute()

            logger.success("Arc database health check passed")
            return True

        except Exception as e:
            logger.error(f"Arc database health check failed: {e}")
            return False
