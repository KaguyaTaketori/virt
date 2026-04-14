from typing import Dict, Optional, Any
from app.models.models import Platform
from app.integrations.base import PlatformClient

_REGISTRY: Dict[Platform, Any] = {}


def register_platform(client: PlatformClient) -> None:
    _REGISTRY[client.platform] = client


def get_platform(platform: Platform) -> Optional[Any]:
    return _REGISTRY.get(platform)
