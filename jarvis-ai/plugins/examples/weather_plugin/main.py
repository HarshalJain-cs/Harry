"""
Weather Plugin - Get weather information.

Demonstrates plugin creation for JARVIS.
"""

import json
import urllib.request
from typing import Dict, List, Optional

# Import from parent - adjust path as needed
import sys
sys.path.insert(0, '../../../')

try:
    from plugins.loader import Plugin
except ImportError:
    # Fallback for standalone testing
    class Plugin:
        def __init__(self, context=None): pass
        def get_name(self): return ""
        def get_description(self): return ""
        def get_tools(self): return []


class WeatherPlugin(Plugin):
    """
    Weather information plugin.
    
    Uses free weather APIs to fetch current conditions.
    """
    
    # Free weather API (wttr.in)
    WEATHER_API = "https://wttr.in/{location}?format=j1"
    
    def get_name(self) -> str:
        return "Weather"
    
    def get_description(self) -> str:
        return "Get weather information for any location"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "handler": self.get_weather,
                "parameters": {
                    "location": "City name or coordinates",
                },
            },
            {
                "name": "weather_forecast",
                "description": "Get weather forecast for a location",
                "handler": self.get_forecast,
                "parameters": {
                    "location": "City name",
                    "days": "Number of days (1-3)",
                },
            },
        ]
    
    def get_weather(self, location: str = "London") -> Dict:
        """
        Get current weather for a location.
        
        Args:
            location: City name or coordinates
            
        Returns:
            Weather data dict
        """
        try:
            url = self.WEATHER_API.format(location=location.replace(" ", "+"))
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            current = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]
            
            return {
                "success": True,
                "location": area.get("areaName", [{}])[0].get("value", location),
                "country": area.get("country", [{}])[0].get("value", ""),
                "temperature_c": current.get("temp_C", "N/A"),
                "temperature_f": current.get("temp_F", "N/A"),
                "feels_like_c": current.get("FeelsLikeC", "N/A"),
                "condition": current.get("weatherDesc", [{}])[0].get("value", "N/A"),
                "humidity": current.get("humidity", "N/A") + "%",
                "wind_kph": current.get("windspeedKmph", "N/A"),
                "wind_dir": current.get("winddir16Point", "N/A"),
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def get_forecast(self, location: str = "London", days: int = 3) -> Dict:
        """
        Get weather forecast.
        
        Args:
            location: City name
            days: Number of forecast days
            
        Returns:
            Forecast data
        """
        try:
            url = self.WEATHER_API.format(location=location.replace(" ", "+"))
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            forecasts = []
            for day in data.get("weather", [])[:days]:
                forecasts.append({
                    "date": day.get("date"),
                    "max_c": day.get("maxtempC"),
                    "min_c": day.get("mintempC"),
                    "condition": day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", ""),
                    "rain_chance": day.get("hourly", [{}])[4].get("chanceofrain", "0") + "%",
                })
            
            return {
                "success": True,
                "location": location,
                "forecast": forecasts,
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def on_load(self):
        """Called when plugin is loaded."""
        print(f"[Weather Plugin] Loaded successfully")
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        print(f"[Weather Plugin] Unloaded")


# Test if run directly
if __name__ == "__main__":
    print("Testing Weather Plugin...")
    
    plugin = WeatherPlugin()
    
    # Test current weather
    weather = plugin.get_weather("New York")
    print(f"\nCurrent weather in {weather.get('location')}:")
    print(f"  Temperature: {weather.get('temperature_c')}°C")
    print(f"  Condition: {weather.get('condition')}")
    print(f"  Humidity: {weather.get('humidity')}")
    
    # Test forecast
    forecast = plugin.get_forecast("London", 3)
    print(f"\nForecast for {forecast.get('location')}:")
    for day in forecast.get("forecast", []):
        print(f"  {day['date']}: {day['condition']} ({day['min_c']}-{day['max_c']}°C)")
    
    print("\nWeather plugin test complete!")
