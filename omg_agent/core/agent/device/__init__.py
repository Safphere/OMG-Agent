"""Device-related utilities."""

from .apps import find_package_name, APP_PACKAGE_MAP
from .screenshot import (
    take_screenshot,
    get_screenshot,  # Alias for backward compatibility
    Screenshot,
    get_current_app,
    is_screen_on,
    wake_screen,
)

__all__ = [
    "find_package_name",
    "APP_PACKAGE_MAP",
    "take_screenshot",
    "get_screenshot",
    "Screenshot",
    "get_current_app",
    "is_screen_on",
    "wake_screen",
]
