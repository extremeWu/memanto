"""
Moorcheh Client Singleton
"""

from fastapi import Depends
from fastapi.params import Depends as DependsType
from moorcheh_sdk import AsyncMoorchehClient, MoorchehClient

from memanto.app.config import settings
from memanto.app.routes.auth_deps import get_moorcheh_api_key


class MoorchehClientSingleton:
    """Singleton pattern for Moorcheh client"""

    _instance = None
    _client = None
    _async_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self, api_key: str | None = None) -> MoorchehClient:
        """Get or create Moorcheh client"""
        key_to_use = api_key or settings.MOORCHEH_API_KEY

        # If using default key, use singleton
        if key_to_use == settings.MOORCHEH_API_KEY:
            if self._client is None:
                self._client = MoorchehClient(api_key=settings.MOORCHEH_API_KEY)
            return self._client

        return MoorchehClient(api_key=key_to_use)

    def get_async_client(self, api_key: str | None = None) -> AsyncMoorchehClient:
        """Get or create Async Moorcheh client"""
        key_to_use = api_key or settings.MOORCHEH_API_KEY

        # If using default key, use singleton
        if key_to_use == settings.MOORCHEH_API_KEY:
            if self._async_client is None:
                self._async_client = AsyncMoorchehClient(
                    api_key=settings.MOORCHEH_API_KEY
                )
            return self._async_client

        return AsyncMoorchehClient(api_key=key_to_use)

    def reset_client(self):
        """Reset client (useful for testing)"""
        self._client = None
        self._async_client = None


# Global client instance
moorcheh_client = MoorchehClientSingleton()


def get_moorcheh_client(
    api_key: str = Depends(get_moorcheh_api_key),
) -> MoorchehClient:
    """Dependency injection function"""
    return moorcheh_client.get_client(api_key)


def get_async_moorcheh_client(
    api_key: str = Depends(get_moorcheh_api_key),
) -> AsyncMoorchehClient:
    """Dependency injection function for async client"""
    return moorcheh_client.get_async_client(api_key)
