"""
JARVIS Plugin Loader - Load and validate plugins.

Handles plugin discovery, validation, and initialization.
"""

import os
import sys
import json
import importlib
import importlib.util
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class PluginMetadata:
    """Plugin metadata from plugin.json."""
    name: str
    version: str
    description: str
    author: str = "Unknown"
    homepage: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_jarvis_version: str = "1.0.0"
    entry_point: str = "main.py"
    enabled: bool = True
    

@dataclass
class PluginInfo:
    """Runtime plugin information."""
    metadata: PluginMetadata
    path: str
    loaded_at: datetime
    status: str = "loaded"  # loaded, error, disabled
    error: Optional[str] = None


class Plugin(ABC):
    """
    Base class for JARVIS plugins.
    
    All plugins should inherit from this class.
    """
    
    def __init__(self, jarvis_context: Dict = None):
        """
        Initialize plugin.
        
        Args:
            jarvis_context: Context from JARVIS including tools registry
        """
        self.context = jarvis_context or {}
        self.tools = self.context.get("tools")
        self.llm = self.context.get("llm")
        self.memory = self.context.get("memory")
    
    @abstractmethod
    def get_name(self) -> str:
        """Return plugin name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return plugin description."""
        pass
    
    def get_version(self) -> str:
        """Return plugin version."""
        return "1.0.0"
    
    @abstractmethod
    def get_tools(self) -> List[Dict]:
        """
        Return list of tools provided by this plugin.
        
        Each tool dict should have:
        - name: Tool name
        - description: Tool description
        - handler: Callable function
        - parameters: Dict of parameter definitions
        """
        pass
    
    def on_load(self):
        """Called when plugin is loaded."""
        pass
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        pass
    
    def on_command(self, command: str) -> Optional[str]:
        """
        Hook called for every command.
        
        Return a response to handle the command,
        or None to let other handlers process it.
        """
        return None


class PluginLoader:
    """
    Load plugins from the plugins directory.
    
    Plugin structure:
    plugins/
        my_plugin/
            plugin.json     # Metadata
            main.py         # Entry point with Plugin subclass
            ...
    """
    
    def __init__(
        self,
        plugins_dir: str = "./plugins",
    ):
        """
        Initialize plugin loader.
        
        Args:
            plugins_dir: Directory containing plugins
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaded_plugins: Dict[str, PluginInfo] = {}
        self.plugin_instances: Dict[str, Plugin] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins.
        
        Returns:
            List of plugin directory names
        """
        plugins = []
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_json = item / "plugin.json"
                if plugin_json.exists():
                    plugins.append(item.name)
        
        return plugins
    
    def load_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Load plugin metadata from plugin.json."""
        plugin_path = self.plugins_dir / plugin_name
        plugin_json = plugin_path / "plugin.json"
        
        if not plugin_json.exists():
            return None
        
        try:
            with open(plugin_json, 'r') as f:
                data = json.load(f)
            
            return PluginMetadata(
                name=data.get("name", plugin_name),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                author=data.get("author", "Unknown"),
                homepage=data.get("homepage", ""),
                dependencies=data.get("dependencies", []),
                min_jarvis_version=data.get("min_jarvis_version", "1.0.0"),
                entry_point=data.get("entry_point", "main.py"),
                enabled=data.get("enabled", True),
            )
        except Exception:
            return None
    
    def load_plugin(
        self,
        plugin_name: str,
        jarvis_context: Dict = None,
    ) -> Optional[Plugin]:
        """
        Load a plugin.
        
        Args:
            plugin_name: Name of plugin directory
            jarvis_context: Context to pass to plugin
            
        Returns:
            Plugin instance or None
        """
        # Load metadata
        metadata = self.load_metadata(plugin_name)
        if not metadata:
            return None
        
        if not metadata.enabled:
            self.loaded_plugins[plugin_name] = PluginInfo(
                metadata=metadata,
                path=str(self.plugins_dir / plugin_name),
                loaded_at=datetime.now(),
                status="disabled",
            )
            return None
        
        plugin_path = self.plugins_dir / plugin_name
        entry_file = plugin_path / metadata.entry_point
        
        if not entry_file.exists():
            self.loaded_plugins[plugin_name] = PluginInfo(
                metadata=metadata,
                path=str(plugin_path),
                loaded_at=datetime.now(),
                status="error",
                error=f"Entry point not found: {metadata.entry_point}",
            )
            return None
        
        try:
            # Add plugin path to sys.path
            plugin_path_str = str(plugin_path)
            if plugin_path_str not in sys.path:
                sys.path.insert(0, plugin_path_str)
            
            # Load module
            spec = importlib.util.spec_from_file_location(
                f"jarvis_plugin_{plugin_name}",
                entry_file,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Plugin subclass
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr is not Plugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                raise ValueError("No Plugin subclass found")
            
            # Instantiate plugin
            instance = plugin_class(jarvis_context)
            instance.on_load()
            
            self.plugin_instances[plugin_name] = instance
            self.loaded_plugins[plugin_name] = PluginInfo(
                metadata=metadata,
                path=str(plugin_path),
                loaded_at=datetime.now(),
                status="loaded",
            )
            
            return instance
        
        except Exception as e:
            self.loaded_plugins[plugin_name] = PluginInfo(
                metadata=metadata,
                path=str(plugin_path),
                loaded_at=datetime.now(),
                status="error",
                error=str(e),
            )
            return None
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name in self.plugin_instances:
            try:
                self.plugin_instances[plugin_name].on_unload()
            except:
                pass
            
            del self.plugin_instances[plugin_name]
            
            if plugin_name in self.loaded_plugins:
                self.loaded_plugins[plugin_name].status = "unloaded"
            
            return True
        return False
    
    def load_all_plugins(self, jarvis_context: Dict = None) -> Dict[str, Plugin]:
        """Load all discovered plugins."""
        plugins = self.discover_plugins()
        
        for plugin_name in plugins:
            self.load_plugin(plugin_name, jarvis_context)
        
        return self.plugin_instances
    
    def get_loaded_plugins(self) -> Dict[str, PluginInfo]:
        """Get info about all loaded plugins."""
        return self.loaded_plugins
    
    def get_plugin_tools(self, plugin_name: str) -> List[Dict]:
        """Get tools from a specific plugin."""
        if plugin_name not in self.plugin_instances:
            return []
        
        try:
            return self.plugin_instances[plugin_name].get_tools()
        except:
            return []
    
    def get_all_plugin_tools(self) -> List[Dict]:
        """Get all tools from all loaded plugins."""
        tools = []
        
        for plugin_name, instance in self.plugin_instances.items():
            try:
                plugin_tools = instance.get_tools()
                for tool in plugin_tools:
                    tool["plugin"] = plugin_name
                tools.extend(plugin_tools)
            except:
                pass
        
        return tools


if __name__ == "__main__":
    print("Testing Plugin Loader...")
    
    loader = PluginLoader(plugins_dir="./test_plugins")
    
    # Create a test plugin
    test_plugin_dir = Path("./test_plugins/hello_world")
    test_plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # plugin.json
    with open(test_plugin_dir / "plugin.json", 'w') as f:
        json.dump({
            "name": "Hello World",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test",
        }, f)
    
    # main.py
    with open(test_plugin_dir / "main.py", 'w') as f:
        f.write('''
from plugins.loader import Plugin

class HelloPlugin(Plugin):
    def get_name(self):
        return "Hello World"
    
    def get_description(self):
        return "Says hello"
    
    def get_tools(self):
        return [{
            "name": "say_hello",
            "description": "Say hello to someone",
            "handler": self.say_hello,
        }]
    
    def say_hello(self, name="World"):
        return f"Hello, {name}!"
''')
    
    # Discover and load
    plugins = loader.discover_plugins()
    print(f"Discovered plugins: {plugins}")
    
    loader.load_all_plugins()
    print(f"Loaded plugins: {list(loader.plugin_instances.keys())}")
    
    for name, info in loader.get_loaded_plugins().items():
        print(f"  {name}: {info.status}")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_plugins"):
        shutil.rmtree("./test_plugins")
    
    print("\nPlugin loader test complete!")
