"""
JARVIS Plugin Manager - High-level plugin management.

Handles plugin lifecycle, tool registration, and updates.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .loader import PluginLoader, Plugin, PluginMetadata, PluginInfo


class PluginManager:
    """
    Manage JARVIS plugins.
    
    Features:
    - Plugin discovery and loading
    - Tool registration with main registry
    - Plugin enable/disable
    - Plugin updates (from URL)
    """
    
    def __init__(
        self,
        plugins_dir: str = "./plugins",
        config_path: str = "./storage/plugins.json",
    ):
        """
        Initialize plugin manager.
        
        Args:
            plugins_dir: Directory for plugins
            config_path: Path for plugin config
        """
        self.plugins_dir = Path(plugins_dir)
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.loader = PluginLoader(str(self.plugins_dir))
        self.config: Dict = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load plugin configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
    
    def _save_config(self):
        """Save plugin configuration."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def initialize(self, jarvis_context: Dict = None):
        """
        Initialize plugin system and load all plugins.
        
        Args:
            jarvis_context: JARVIS context to pass to plugins
        """
        self.loader.load_all_plugins(jarvis_context)
        self._register_plugin_tools()
    
    def _register_plugin_tools(self):
        """Register plugin tools with the main tool registry."""
        try:
            from tools.registry import get_registry, Tool, RiskLevel
            registry = get_registry()
            
            for plugin_name, instance in self.loader.plugin_instances.items():
                try:
                    tools = instance.get_tools()
                    
                    for tool_def in tools:
                        tool = Tool(
                            name=f"plugin_{plugin_name}_{tool_def['name']}",
                            description=tool_def.get('description', ''),
                            handler=tool_def['handler'],
                            parameters=tool_def.get('parameters', {}),
                            category=f"plugin:{plugin_name}",
                            risk_level=RiskLevel.LOW,
                        )
                        registry.register(tool)
                except Exception as e:
                    print(f"Failed to register tools from {plugin_name}: {e}")
        except ImportError:
            pass
    
    def list_plugins(self) -> List[Dict]:
        """List all available plugins."""
        plugins = []
        
        discovered = self.loader.discover_plugins()
        loaded = self.loader.get_loaded_plugins()
        
        for name in discovered:
            info = loaded.get(name)
            metadata = self.loader.load_metadata(name)
            
            plugins.append({
                "name": name,
                "display_name": metadata.name if metadata else name,
                "version": metadata.version if metadata else "unknown",
                "description": metadata.description if metadata else "",
                "author": metadata.author if metadata else "Unknown",
                "status": info.status if info else "not_loaded",
                "enabled": self.is_enabled(name),
            })
        
        return plugins
    
    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get info about a specific plugin."""
        return self.loader.loaded_plugins.get(name)
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        self.config.setdefault("disabled", [])
        
        if name in self.config["disabled"]:
            self.config["disabled"].remove(name)
            self._save_config()
        
        # Update plugin.json
        plugin_json = self.plugins_dir / name / "plugin.json"
        if plugin_json.exists():
            try:
                with open(plugin_json, 'r') as f:
                    data = json.load(f)
                data["enabled"] = True
                with open(plugin_json, 'w') as f:
                    json.dump(data, f, indent=2)
            except:
                pass
        
        return True
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        self.config.setdefault("disabled", [])
        
        if name not in self.config["disabled"]:
            self.config["disabled"].append(name)
            self._save_config()
        
        # Unload if loaded
        self.loader.unload_plugin(name)
        
        # Update plugin.json
        plugin_json = self.plugins_dir / name / "plugin.json"
        if plugin_json.exists():
            try:
                with open(plugin_json, 'r') as f:
                    data = json.load(f)
                data["enabled"] = False
                with open(plugin_json, 'w') as f:
                    json.dump(data, f, indent=2)
            except:
                pass
        
        return True
    
    def is_enabled(self, name: str) -> bool:
        """Check if plugin is enabled."""
        disabled = self.config.get("disabled", [])
        return name not in disabled
    
    def reload_plugin(self, name: str, jarvis_context: Dict = None) -> bool:
        """Reload a plugin."""
        self.loader.unload_plugin(name)
        instance = self.loader.load_plugin(name, jarvis_context)
        
        if instance:
            self._register_plugin_tools()
            return True
        return False
    
    def install_from_directory(self, source_dir: str) -> Optional[str]:
        """
        Install plugin from a directory.
        
        Args:
            source_dir: Directory containing the plugin
            
        Returns:
            Plugin name if successful
        """
        source = Path(source_dir)
        
        if not (source / "plugin.json").exists():
            return None
        
        # Get plugin name from metadata
        try:
            with open(source / "plugin.json", 'r') as f:
                data = json.load(f)
            plugin_name = data.get("name", source.name)
        except:
            plugin_name = source.name
        
        # Copy to plugins directory
        dest = self.plugins_dir / plugin_name.lower().replace(" ", "_")
        if dest.exists():
            shutil.rmtree(dest)
        
        shutil.copytree(source, dest)
        
        return plugin_name
    
    def uninstall_plugin(self, name: str) -> bool:
        """Uninstall a plugin."""
        self.loader.unload_plugin(name)
        
        plugin_path = self.plugins_dir / name
        if plugin_path.exists():
            shutil.rmtree(plugin_path)
            return True
        return False
    
    def create_plugin_template(self, name: str) -> str:
        """
        Create a new plugin template.
        
        Args:
            name: Plugin name
            
        Returns:
            Path to created plugin
        """
        safe_name = name.lower().replace(" ", "_")
        plugin_path = self.plugins_dir / safe_name
        plugin_path.mkdir(parents=True, exist_ok=True)
        
        # plugin.json
        with open(plugin_path / "plugin.json", 'w') as f:
            json.dump({
                "name": name,
                "version": "1.0.0",
                "description": f"A JARVIS plugin: {name}",
                "author": "Your Name",
                "entry_point": "main.py",
                "enabled": True,
            }, f, indent=2)
        
        # main.py
        with open(plugin_path / "main.py", 'w') as f:
            f.write(f'''"""
{name} - A JARVIS Plugin
"""

from plugins.loader import Plugin


class {safe_name.title().replace("_", "")}Plugin(Plugin):
    """Main plugin class."""
    
    def get_name(self) -> str:
        return "{name}"
    
    def get_description(self) -> str:
        return "Description of your plugin"
    
    def get_tools(self) -> list:
        return [
            {{
                "name": "example_tool",
                "description": "An example tool",
                "handler": self.example_tool,
                "parameters": {{"text": "string"}},
            }},
        ]
    
    def example_tool(self, text: str = "Hello") -> str:
        """Example tool implementation."""
        return f"Plugin says: {{text}}"
    
    def on_load(self):
        """Called when plugin is loaded."""
        print(f"{{self.get_name()}} loaded!")
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        print(f"{{self.get_name()}} unloaded!")
''')
        
        return str(plugin_path)


from tools.registry import tool, ToolResult


@tool(
    name="list_plugins",
    description="List installed JARVIS plugins",
    category="plugins",
)
def list_plugins() -> ToolResult:
    """List plugins."""
    try:
        manager = PluginManager()
        plugins = manager.list_plugins()
        
        return ToolResult(
            success=True,
            output=plugins,
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="enable_plugin",
    description="Enable a JARVIS plugin",
    category="plugins",
)
def enable_plugin(name: str) -> ToolResult:
    """Enable plugin."""
    try:
        manager = PluginManager()
        success = manager.enable_plugin(name)
        
        return ToolResult(
            success=success,
            output=f"Plugin '{name}' enabled" if success else "Failed",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="disable_plugin",
    description="Disable a JARVIS plugin",
    category="plugins",
)
def disable_plugin(name: str) -> ToolResult:
    """Disable plugin."""
    try:
        manager = PluginManager()
        success = manager.disable_plugin(name)
        
        return ToolResult(
            success=success,
            output=f"Plugin '{name}' disabled" if success else "Failed",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="create_plugin",
    description="Create a new plugin template",
    category="plugins",
)
def create_plugin(name: str) -> ToolResult:
    """Create plugin template."""
    try:
        manager = PluginManager()
        path = manager.create_plugin_template(name)
        
        return ToolResult(
            success=True,
            output=f"Plugin created: {path}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Plugin Manager...")
    
    manager = PluginManager(
        plugins_dir="./test_plugins_mgr",
        config_path="./test_plugin_config.json",
    )
    
    # Create template
    path = manager.create_plugin_template("My Test Plugin")
    print(f"Created plugin: {path}")
    
    # List plugins
    plugins = manager.list_plugins()
    print(f"Plugins: {len(plugins)}")
    
    for p in plugins:
        print(f"  - {p['name']}: {p['status']}")
    
    # Cleanup
    import os
    if os.path.exists("./test_plugins_mgr"):
        shutil.rmtree("./test_plugins_mgr")
    if os.path.exists("./test_plugin_config.json"):
        os.remove("./test_plugin_config.json")
    
    print("\nPlugin manager test complete!")
