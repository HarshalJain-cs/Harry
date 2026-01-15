"""
JARVIS Smart Home Integration - IoT device control.

Provides integration with smart home platforms (Home Assistant, etc.)
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SmartDevice:
    """A smart home device."""
    id: str
    name: str
    type: str  # light, switch, thermostat, sensor, etc.
    state: Dict[str, Any]
    room: Optional[str] = None
    platform: str = "generic"


@dataclass
class DeviceState:
    """Device state snapshot."""
    device_id: str
    state: Dict[str, Any]
    timestamp: datetime


class SmartHomeHub:
    """
    Smart home device control hub.
    
    Features:
    - Device registration
    - State management
    - Room grouping
    - Scene automation
    - Home Assistant integration (optional)
    """
    
    def __init__(
        self,
        config_path: str = "./storage/smart_home.json",
        home_assistant_url: Optional[str] = None,
        home_assistant_token: Optional[str] = None,
    ):
        """
        Initialize smart home hub.
        
        Args:
            config_path: Path for device config
            home_assistant_url: Home Assistant URL
            home_assistant_token: HA Long-lived access token
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.ha_url = home_assistant_url
        self.ha_token = home_assistant_token
        
        self.devices: Dict[str, SmartDevice] = {}
        self.rooms: Dict[str, List[str]] = {}
        self.scenes: Dict[str, Dict] = {}
        
        self._load()
    
    def _load(self):
        """Load device configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for device_data in data.get("devices", []):
                    device = SmartDevice(**device_data)
                    self.devices[device.id] = device
                
                self.rooms = data.get("rooms", {})
                self.scenes = data.get("scenes", {})
            except Exception:
                pass
    
    def _save(self):
        """Save configuration."""
        data = {
            "devices": [asdict(d) for d in self.devices.values()],
            "rooms": self.rooms,
            "scenes": self.scenes,
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_device(
        self,
        name: str,
        device_type: str,
        room: str = None,
        initial_state: Dict = None,
    ) -> SmartDevice:
        """
        Add a device.
        
        Args:
            name: Device name
            device_type: Device type
            room: Room location
            initial_state: Initial state
            
        Returns:
            SmartDevice
        """
        device_id = f"device_{len(self.devices)}_{datetime.now().timestamp()}"
        
        device = SmartDevice(
            id=device_id,
            name=name,
            type=device_type,
            state=initial_state or {"on": False},
            room=room,
        )
        
        self.devices[device_id] = device
        
        if room:
            self.rooms.setdefault(room, [])
            self.rooms[room].append(device_id)
        
        self._save()
        return device
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device."""
        if device_id in self.devices:
            device = self.devices[device_id]
            
            if device.room and device.room in self.rooms:
                self.rooms[device.room] = [
                    d for d in self.rooms[device.room] if d != device_id
                ]
            
            del self.devices[device_id]
            self._save()
            return True
        return False
    
    def get_device(self, device_id: str) -> Optional[SmartDevice]:
        """Get device by ID."""
        return self.devices.get(device_id)
    
    def find_device(self, name: str) -> Optional[SmartDevice]:
        """Find device by name."""
        name_lower = name.lower()
        for device in self.devices.values():
            if name_lower in device.name.lower():
                return device
        return None
    
    def list_devices(self, room: str = None, device_type: str = None) -> List[SmartDevice]:
        """List devices with optional filters."""
        devices = list(self.devices.values())
        
        if room:
            devices = [d for d in devices if d.room == room]
        
        if device_type:
            devices = [d for d in devices if d.type == device_type]
        
        return devices
    
    def set_state(self, device_id: str, state: Dict) -> Optional[SmartDevice]:
        """Set device state."""
        if device_id not in self.devices:
            return None
        
        device = self.devices[device_id]
        device.state.update(state)
        self._save()
        
        return device
    
    def turn_on(self, device_id: str) -> Optional[SmartDevice]:
        """Turn on a device."""
        return self.set_state(device_id, {"on": True})
    
    def turn_off(self, device_id: str) -> Optional[SmartDevice]:
        """Turn off a device."""
        return self.set_state(device_id, {"on": False})
    
    def toggle(self, device_id: str) -> Optional[SmartDevice]:
        """Toggle device state."""
        if device_id not in self.devices:
            return None
        
        device = self.devices[device_id]
        current = device.state.get("on", False)
        return self.set_state(device_id, {"on": not current})
    
    def set_brightness(self, device_id: str, brightness: int) -> Optional[SmartDevice]:
        """Set light brightness (0-100)."""
        brightness = max(0, min(100, brightness))
        return self.set_state(device_id, {"brightness": brightness, "on": brightness > 0})
    
    def set_temperature(self, device_id: str, temperature: float) -> Optional[SmartDevice]:
        """Set thermostat temperature."""
        return self.set_state(device_id, {"target_temp": temperature})
    
    # Room controls
    def control_room(self, room: str, state: Dict) -> List[SmartDevice]:
        """Control all devices in a room."""
        controlled = []
        
        device_ids = self.rooms.get(room, [])
        for device_id in device_ids:
            device = self.set_state(device_id, state)
            if device:
                controlled.append(device)
        
        return controlled
    
    def room_on(self, room: str) -> List[SmartDevice]:
        """Turn on all devices in room."""
        return self.control_room(room, {"on": True})
    
    def room_off(self, room: str) -> List[SmartDevice]:
        """Turn off all devices in room."""
        return self.control_room(room, {"on": False})
    
    # Scenes
    def create_scene(self, name: str, device_states: Dict[str, Dict]) -> bool:
        """
        Create a scene.
        
        Args:
            name: Scene name
            device_states: Dict of device_id -> state
        """
        self.scenes[name] = {
            "name": name,
            "states": device_states,
            "created": datetime.now().isoformat(),
        }
        self._save()
        return True
    
    def activate_scene(self, name: str) -> List[SmartDevice]:
        """Activate a scene."""
        if name not in self.scenes:
            return []
        
        scene = self.scenes[name]
        controlled = []
        
        for device_id, state in scene.get("states", {}).items():
            device = self.set_state(device_id, state)
            if device:
                controlled.append(device)
        
        return controlled
    
    def list_scenes(self) -> List[str]:
        """List available scenes."""
        return list(self.scenes.keys())
    
    # Home Assistant integration
    def sync_home_assistant(self) -> int:
        """
        Sync devices from Home Assistant.
        
        Returns:
            Number of devices synced
        """
        if not self.ha_url or not self.ha_token:
            return 0
        
        try:
            import urllib.request
            
            request = urllib.request.Request(
                f"{self.ha_url}/api/states",
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                },
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                states = json.loads(response.read().decode())
            
            count = 0
            for entity in states:
                entity_id = entity.get("entity_id", "")
                
                # Filter for common device types
                if any(entity_id.startswith(t) for t in ["light.", "switch.", "climate."]):
                    device_type = entity_id.split(".")[0]
                    
                    device = SmartDevice(
                        id=entity_id,
                        name=entity.get("attributes", {}).get("friendly_name", entity_id),
                        type=device_type,
                        state={"on": entity.get("state") == "on"},
                        platform="home_assistant",
                    )
                    
                    self.devices[entity_id] = device
                    count += 1
            
            self._save()
            return count
        
        except Exception:
            return 0


from tools.registry import tool, ToolResult


@tool(
    name="smart_device",
    description="Control a smart home device",
    category="smart_home",
    examples=["turn on living room lights", "set bedroom temperature to 72"],
)
def smart_device(
    action: str,
    device_name: str,
    value: Any = None,
) -> ToolResult:
    """Control smart device."""
    try:
        hub = SmartHomeHub()
        device = hub.find_device(device_name)
        
        if not device:
            return ToolResult(success=False, error=f"Device not found: {device_name}")
        
        if action == "on":
            result = hub.turn_on(device.id)
        elif action == "off":
            result = hub.turn_off(device.id)
        elif action == "toggle":
            result = hub.toggle(device.id)
        elif action == "brightness" and value is not None:
            result = hub.set_brightness(device.id, int(value))
        elif action == "temperature" and value is not None:
            result = hub.set_temperature(device.id, float(value))
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")
        
        if result:
            return ToolResult(
                success=True,
                output={
                    "device": result.name,
                    "state": result.state,
                },
            )
        return ToolResult(success=False, error="Failed to control device")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_smart_devices",
    description="List smart home devices",
    category="smart_home",
)
def list_smart_devices(room: str = None) -> ToolResult:
    """List devices."""
    try:
        hub = SmartHomeHub()
        devices = hub.list_devices(room=room)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "name": d.name,
                    "type": d.type,
                    "room": d.room,
                    "on": d.state.get("on", False),
                }
                for d in devices
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="activate_scene",
    description="Activate a smart home scene",
    category="smart_home",
    examples=["activate movie night scene", "set scene to bedtime"],
)
def activate_scene(scene_name: str) -> ToolResult:
    """Activate scene."""
    try:
        hub = SmartHomeHub()
        devices = hub.activate_scene(scene_name)
        
        if devices:
            return ToolResult(
                success=True,
                output=f"Activated scene '{scene_name}' ({len(devices)} devices)",
            )
        return ToolResult(success=False, error=f"Scene not found: {scene_name}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Smart Home Hub...")
    
    hub = SmartHomeHub(config_path="./test_smart_home.json")
    
    # Add devices
    living_light = hub.add_device("Living Room Light", "light", room="living_room")
    bedroom_light = hub.add_device("Bedroom Light", "light", room="bedroom")
    thermostat = hub.add_device("Thermostat", "thermostat", room="living_room")
    
    print(f"Added {len(hub.devices)} devices")
    
    # Control
    hub.turn_on(living_light.id)
    hub.set_brightness(bedroom_light.id, 50)
    hub.set_temperature(thermostat.id, 72)
    
    # List
    for device in hub.list_devices():
        print(f"  {device.name}: {device.state}")
    
    # Scene
    hub.create_scene("Movie Night", {
        living_light.id: {"on": True, "brightness": 20},
        bedroom_light.id: {"on": False},
    })
    print(f"Scenes: {hub.list_scenes()}")
    
    # Cleanup
    if os.path.exists("./test_smart_home.json"):
        os.remove("./test_smart_home.json")
    
    print("\nSmart home test complete!")
