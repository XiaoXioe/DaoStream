from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The user-facing name of the source (e.g., 'Anichin')."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """The base URL of the website source (e.g., 'https://anichin.moe')."""
        pass

    @abstractmethod
    def get_latest(self) -> List[Dict[str, str]]:
        """Fetch latest releases. Returns list of {'title': str, 'link': str}"""
        pass

    @abstractmethod
    def get_popular(self) -> List[Dict[str, str]]:
        """Fetch popular today releases. Returns list of {'title': str, 'link': str}"""
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, str]]:
        """Search for anime series. Returns list of {'title': str, 'link': str}"""
        pass

    @abstractmethod
    def get_episodes(self, anime_url: str) -> List[Dict[str, str]]:
        """Fetch all episodes for a given anime URL. Returns list of {'name': str, 'link': str}"""
        pass

    @abstractmethod
    def get_servers(self, ep_url: str) -> List[Dict[str, Any]]:
        """Fetch servers for a given episode URL. Returns list of {'name': str, 'value': str, 'type': str}"""
        pass
