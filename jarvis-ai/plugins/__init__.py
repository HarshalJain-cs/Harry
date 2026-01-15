"""
JARVIS Plugin System - Extensible plugin architecture.

Allows loading external plugins to extend JARVIS functionality.
"""

from .loader import PluginLoader, Plugin, PluginMetadata
from .manager import PluginManager

__all__ = [
    "PluginLoader",
    "Plugin",
    "PluginMetadata",
    "PluginManager",
]
