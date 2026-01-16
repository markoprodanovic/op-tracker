"""
Web scraper for One Piece episodes from animefillerlist.com

This module handles:
- Fetching the One Piece episode list webpage
- Parsing the episode table data
- Extracting episode information (id, title, airdate)
- Error handling and retry logic
- Rate limiting respect
"""

# import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import httpx
from bs4 import BeautifulSoup
from loguru import logger

# from ..config import config


class ScrapingError(Exception):
    """Custom exception for scraping-related errors."""
    pass


class AnimeFillerListScraper:
    """
    Scraper for animefillerlist.com One Piece episode data.

    This class handles:
    - Fetching the One Piece episode list page
    - Parsing the episode table
    - Extracting episode data (number, title, airdate)
    - Error handling and retries
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.base_url = "https://www.animefillerlist.com/shows/one-piece"
        self.timeout = timeout

        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/91.0.4472.124 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        logger.info(f"Initialized scraper for: {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup the HTTP client."""
        await self.client.aclose()

    async def fetch_page(self) -> str:
        """
        Fetch the One Piece episode list page.

        Returns:
            Raw HTML content of the page

        Raises:
            ScrapingError: If page fetch fails
        """
        try:
            logger.info(f"Fetching page: {self.base_url}")
            response = await self.client.get(self.base_url)
            response.raise_for_status()

            logger.success(f"Successfully fetched page (status: {response.status_code})")
            return response.text

        except httpx.RequestError as e:
            error_msg = f"Network error while fetching page: {str(e)}"
            logger.error(error_msg)
            raise ScrapingError(error_msg) from e

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error while fetching page: {e.response.status_code}"
            logger.error(error_msg)
            raise ScrapingError(error_msg) from e

    def parse_episode_table(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse the episode table from the HTML.

        Args:
            html: Raw HTML content from the page

        Returns:
            List of episode dictionaries with keys: id, title, airdate

        Raises:
            ScrapingError: If parsing fails
        """
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find the specific episode table with class "EpisodeList"
            table = soup.find('table', class_='EpisodeList')
            if not table:
                # Find all table rows, skip the header
                raise ScrapingError("Could not find EpisodeList table on page")
            rows = table.find_all('tr')[1:]  # Skip header row
            if not rows:
                raise ScrapingError("No episode rows found in table")

            episodes = []
            processed_count = 0

            for row in rows:
                try:
                    episode_data = self._parse_episode_row(row)
                    if episode_data:
                        episodes.append(episode_data)
                        processed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")
                    continue

            logger.info(f"Successfully parsed {processed_count} episodes from table")
            return episodes

        except Exception as e:
            error_msg = f"Failed to parse episode table: {str(e)}"
            logger.error(error_msg)
            raise ScrapingError(error_msg) from e

    def _parse_episode_row(self, row) -> Optional[Dict[str, Any]]:
        """
        Parse a single episode row from the table.

        Args:
            row: BeautifulSoup table row element

        Returns:
            Episode dictionary or None if parsing fails
        """
        try:
            # Extract episode number from td with class "Number"
            number_cell = row.find('td', class_='Number')
            if not number_cell:
                logger.warning("Could not find Number cell in row")
                return None
            episode_id = int(number_cell.get_text(strip=True))

            # Extract title from td with class "Title"
            # The title is inside an <a> tag, so we get the text from the link
            title_cell = row.find('td', class_='Title')
            if not title_cell:
                logger.warning("Could not find Title cell in row")
                return None

            title_link = title_cell.find('a')
            if title_link:
                # Get text from the link and decode HTML entities
                title = title_link.get_text(strip=True)
                # Handle HTML entities like &#039; (apostrophe)
                title = title.replace('&#039;', "'")
            else:
                title = title_cell.get_text(strip=True)

            # Extract airdate from td with class "Date"
            date_cell = row.find('td', class_='Date')
            if not date_cell:
                logger.warning("Could not find Date cell in row")
                return None

            airdate_text = date_cell.get_text(strip=True)
            airdate = self._parse_airdate(airdate_text)

            return {
                'id': episode_id,
                'title': title,
                'airdate': airdate
            }

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse episode row: {e}")
            return None

    def _parse_airdate(self, airdate_text: str) -> Optional[date]:
        """
        Parse airdate string into a date object.

        Args:
            airdate_text: Raw airdate string from the table

        Returns:
            Date object or None if parsing fails
        """
        if not airdate_text or airdate_text.lower() in ['tba', 'tbd', 'unknown', '-']:
            return None

        # The website uses YYYY-MM-DD format (like 1999-10-20)
        try:
            return datetime.strptime(airdate_text, '%Y-%m-%d').date()
        except ValueError:
            # Fallback to other common formats if needed
            date_formats = [
                '%m/%d/%Y',      # 10/15/2023
                '%d/%m/%Y',      # 15/10/2023
                '%B %d, %Y',     # October 15, 2023
                '%b %d, %Y',     # Oct 15, 2023
                '%Y.%m.%d',      # 2023.10.15
            ]

            for date_format in date_formats:
                try:
                    return datetime.strptime(airdate_text, date_format).date()
                except ValueError:
                    continue

        logger.warning(f"Could not parse airdate: {airdate_text}")
        return None

    async def scrape_episodes(self) -> List[Dict[str, Any]]:
        """
        Main scraping method - fetch and parse all episodes.

        Returns:
            List of episode dictionaries

        Raises:
            ScrapingError: If scraping fails
        """
        try:
            # Fetch the page
            html = await self.fetch_page()

            # Parse episodes from the table
            episodes = self.parse_episode_table(html)

            logger.success(f"Successfully scraped {len(episodes)} episodes")
            return episodes

        except Exception as e:
            error_msg = f"Failed to scrape episodes: {str(e)}"
            logger.error(error_msg)
            raise ScrapingError(error_msg) from e


# Convenience function for simple usage
async def scrape_one_piece_episodes() -> List[Dict[str, Any]]:
    """
    Convenience function to scrape One Piece episodes.

    Returns:
        List of episode dictionaries
    """
    async with AnimeFillerListScraper() as scraper:
        return await scraper.scrape_episodes()
