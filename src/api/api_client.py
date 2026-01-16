import asyncio
from typing import Optional
import httpx
from loguru import logger

from ..config import config
from ..models import EpisodeFromAPI, APIEpisodeList


class OnePieceAPIError(Exception):
    pass


class OnePieceAPIClient:
    """
    Client for interacting with the One Piece API.

    This class handles:
    - Fetching all episodes
    - Fetching individual episodes by ID
    - Error handling and retries
    - Rate limiting respect
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for the API (defaults to config value)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.one_piece_api_base_url
        self.timeout = timeout

        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                'Accept': 'application/json',
            }
        )

        logger.info(f"Initialized API client with base URL: {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup the HTTP client."""
        await self.client.aclose()

    async def fetch_all_episodes(self) -> APIEpisodeList:
        """
        Fetch all episodes from the API.

        Returns:
            List of EpisodeFromAPI objects

        Raises:
            OnePieceAPIError: If the API request fails
        """
        url = f"{self.base_url}/episodes/en"
        logger.info(f"Fetching all episodes from: {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched {len(data)} episodes from API")

            episodes = []
            for episode_data in data:
                try:
                    episode = EpisodeFromAPI(**episode_data)
                    episodes.append(episode)
                except Exception as e:
                    logger.warning(f"Failed to parse episode {episode_data.get('id', 'unknown')}: {e}")
                    # Continue processing other episodes even if one fails
                    continue

            logger.success(f"Successfully parsed {len(episodes)} episodes")
            return episodes

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} when fetching episodes: {e.response.text}"
            logger.error(error_msg)
            raise OnePieceAPIError(error_msg) from e

        except httpx.RequestError as e:
            error_msg = f"Network error when fetching episodes: {str(e)}"
            logger.error(error_msg)
            raise OnePieceAPIError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error when fetching episodes: {str(e)}"
            logger.error(error_msg)
            raise OnePieceAPIError(error_msg) from e

    async def fetch_episode_by_id(self, episode_id: int) -> Optional[EpisodeFromAPI]:
        """
        Fetch a specific episode by its ID.

        Args:
            episode_id: The ID of the episode to fetch

        Returns:
            EpisodeFromAPI object if found, None if not found

        Raises:
            OnePieceAPIError: If the API request fails (except for 404)
        """
        url = f"{self.base_url}/episodes/en/{episode_id}"
        logger.info(f"Fetching episode {episode_id} from: {url}")

        try:
            response = await self.client.get(url)

            if response.status_code == 404:
                logger.info(f"Episode {episode_id} not found (404)")
                return None

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()

            try:
                data = response.json()
                logger.debug(f"Parsed JSON data type: {type(data)}, value: {data}")
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response for episode {episode_id}: {json_error}")
                logger.debug(f"Response content: {response.text[:200]}...")
                raise OnePieceAPIError(f"Invalid JSON response for episode {episode_id}")

            if data is None:
                logger.info(f"Episode {episode_id} returned null JSON response")
                return None

            if not isinstance(data, dict):
                logger.warning(f"Episode {episode_id} returned non-dict response: {type(data)}")
                return None

            episode = EpisodeFromAPI(**data)

            logger.success(f"Successfully fetched episode {episode_id}: {episode.title}")
            return episode

        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:  # We handle 404 above
                error_msg = f"HTTP error {e.response.status_code} when fetching episode {episode_id}: {e.response.text}"
                logger.error(error_msg)
                raise OnePieceAPIError(error_msg) from e

        except httpx.RequestError as e:
            error_msg = f"Network error when fetching episode {episode_id}: {str(e)}"
            logger.error(error_msg)
            raise OnePieceAPIError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error when fetching episode {episode_id}: {str(e)}"
            logger.error(error_msg)
            raise OnePieceAPIError(error_msg) from e

    async def fetch_episodes_batch(self, episode_ids: list[int]) -> APIEpisodeList:
        """
        Fetch multiple episodes by their IDs in parallel.

        This method fetches episodes concurrently for better performance,
        but respects rate limits by limiting concurrent requests.

        Args:
            episode_ids: List of episode IDs to fetch

        Returns:
            List of successfully fetched episodes (may be fewer than requested)
        """
        logger.info(f"Fetching {len(episode_ids)} episodes in batch")

        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

        async def fetch_one(episode_id: int) -> Optional[EpisodeFromAPI]:
            async with semaphore:
                return await self.fetch_episode_by_id(episode_id)

        tasks = [fetch_one(episode_id) for episode_id in episode_ids]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        episodes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch episode {episode_ids[i]}: {result}")
            elif result is not None:
                episodes.append(result)

        logger.success(f"Successfully fetched {len(episodes)} out of {len(episode_ids)} requested episodes")
        return episodes

    async def health_check(self) -> bool:
        """
        Check if the One Piece API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to fetch just one episode to test connectivity
            response = await self.client.get(f"{self.base_url}/episodes/en/1")
            is_healthy = response.status_code in (200, 404)  # 404 is OK too

            if is_healthy:
                logger.success("One Piece API health check passed")
            else:
                logger.warning(f"One Piece API health check failed: {response.status_code}")

            return is_healthy

        except Exception as e:
            logger.error(f"One Piece API health check failed: {e}")
            return False
