"""
Database package for One Piece Tracker.

Contains all database-related operations for both API and scraped data.
"""

from .database import EpisodeDatabase, DatabaseError
from .scraped_database import ScrapedEpisodeDatabase, ScrapedEpisodeDatabaseError
from .arc_database import ArcDatabase, ArcDatabaseError

__all__ = [
    'EpisodeDatabase',
    'DatabaseError',
    'ScrapedEpisodeDatabase',
    'ScrapedEpisodeDatabaseError',
    'ArcDatabase',
    'ArcDatabaseError'
]
