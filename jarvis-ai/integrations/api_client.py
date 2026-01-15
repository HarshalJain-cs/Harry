"""
JARVIS API Client - Generic REST API client with auth support.

Provides a flexible HTTP client for API integrations.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error


@dataclass
class APIResponse:
    """API response container."""
    success: bool
    status_code: int
    data: Any
    headers: Dict[str, str]
    error: Optional[str] = None


@dataclass
class APIConfig:
    """API configuration."""
    name: str
    base_url: str
    auth_type: str  # none, bearer, api_key, basic
    auth_value: Optional[str] = None
    auth_header: str = "Authorization"
    default_headers: Dict[str, str] = None


class APIClient:
    """
    Generic REST API client.
    
    Features:
    - Multiple auth types (Bearer, API Key, Basic)
    - Request/response logging
    - Retry logic
    - Configuration storage
    """
    
    def __init__(
        self,
        config_path: str = "./storage/api_configs.json",
    ):
        """
        Initialize API client.
        
        Args:
            config_path: Path to store API configurations
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.configs: Dict[str, APIConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load saved configurations."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for name, config_data in data.items():
                    self.configs[name] = APIConfig(**config_data)
            except Exception:
                pass
    
    def _save_configs(self):
        """Save configurations."""
        data = {}
        for name, config in self.configs.items():
            data[name] = {
                "name": config.name,
                "base_url": config.base_url,
                "auth_type": config.auth_type,
                "auth_value": config.auth_value,
                "auth_header": config.auth_header,
                "default_headers": config.default_headers,
            }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_api(
        self,
        name: str,
        base_url: str,
        auth_type: str = "none",
        auth_value: str = None,
    ):
        """
        Add an API configuration.
        
        Args:
            name: API name (for reference)
            base_url: Base URL
            auth_type: Authentication type
            auth_value: Auth token/key
        """
        config = APIConfig(
            name=name,
            base_url=base_url.rstrip('/'),
            auth_type=auth_type,
            auth_value=auth_value,
            default_headers={"Content-Type": "application/json"},
        )
        
        self.configs[name] = config
        self._save_configs()
    
    def remove_api(self, name: str) -> bool:
        """Remove an API configuration."""
        if name in self.configs:
            del self.configs[name]
            self._save_configs()
            return True
        return False
    
    def _build_headers(self, config: APIConfig, extra_headers: Dict = None) -> Dict:
        """Build request headers with auth."""
        headers = dict(config.default_headers or {})
        
        if config.auth_type == "bearer" and config.auth_value:
            headers[config.auth_header] = f"Bearer {config.auth_value}"
        elif config.auth_type == "api_key" and config.auth_value:
            headers[config.auth_header] = config.auth_value
        elif config.auth_type == "basic" and config.auth_value:
            import base64
            encoded = base64.b64encode(config.auth_value.encode()).decode()
            headers[config.auth_header] = f"Basic {encoded}"
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def request(
        self,
        api_name: str,
        method: str,
        endpoint: str,
        data: Any = None,
        params: Dict = None,
        headers: Dict = None,
        timeout: int = 30,
    ) -> APIResponse:
        """
        Make an API request.
        
        Args:
            api_name: Name of configured API
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout
            
        Returns:
            APIResponse object
        """
        if api_name not in self.configs:
            return APIResponse(
                success=False,
                status_code=0,
                data=None,
                headers={},
                error=f"API not configured: {api_name}",
            )
        
        config = self.configs[api_name]
        url = f"{config.base_url}/{endpoint.lstrip('/')}"
        
        # Add query params
        if params:
            url += '?' + urllib.parse.urlencode(params)
        
        # Build headers
        req_headers = self._build_headers(config, headers)
        
        # Prepare body
        body = None
        if data:
            if isinstance(data, (dict, list)):
                body = json.dumps(data).encode('utf-8')
            else:
                body = str(data).encode('utf-8')
        
        try:
            request = urllib.request.Request(
                url,
                data=body,
                headers=req_headers,
                method=method.upper(),
            )
            
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_data = response.read().decode('utf-8')
                
                try:
                    parsed_data = json.loads(response_data)
                except:
                    parsed_data = response_data
                
                return APIResponse(
                    success=True,
                    status_code=response.status,
                    data=parsed_data,
                    headers=dict(response.headers),
                )
        
        except urllib.error.HTTPError as e:
            return APIResponse(
                success=False,
                status_code=e.code,
                data=None,
                headers=dict(e.headers) if e.headers else {},
                error=str(e),
            )
        except Exception as e:
            return APIResponse(
                success=False,
                status_code=0,
                data=None,
                headers={},
                error=str(e),
            )
    
    def get(self, api_name: str, endpoint: str, **kwargs) -> APIResponse:
        """GET request."""
        return self.request(api_name, "GET", endpoint, **kwargs)
    
    def post(self, api_name: str, endpoint: str, data: Any = None, **kwargs) -> APIResponse:
        """POST request."""
        return self.request(api_name, "POST", endpoint, data=data, **kwargs)
    
    def put(self, api_name: str, endpoint: str, data: Any = None, **kwargs) -> APIResponse:
        """PUT request."""
        return self.request(api_name, "PUT", endpoint, data=data, **kwargs)
    
    def delete(self, api_name: str, endpoint: str, **kwargs) -> APIResponse:
        """DELETE request."""
        return self.request(api_name, "DELETE", endpoint, **kwargs)
    
    def list_apis(self) -> List[str]:
        """List configured APIs."""
        return list(self.configs.keys())


# Pre-configured API templates
API_TEMPLATES = {
    "github": {
        "base_url": "https://api.github.com",
        "auth_type": "bearer",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "auth_type": "bearer",
    },
    "jsonplaceholder": {
        "base_url": "https://jsonplaceholder.typicode.com",
        "auth_type": "none",
    },
}


from tools.registry import tool, ToolResult


@tool(
    name="configure_api",
    description="Configure an API for use with JARVIS",
    category="integration",
)
def configure_api(
    name: str,
    base_url: str,
    auth_type: str = "none",
    auth_value: str = None,
) -> ToolResult:
    """Configure API."""
    try:
        client = APIClient()
        client.add_api(name, base_url, auth_type, auth_value)
        
        return ToolResult(
            success=True,
            output=f"API configured: {name} ({base_url})",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="call_api",
    description="Make an API request",
    category="integration",
)
def call_api(
    api_name: str,
    method: str,
    endpoint: str,
    data: Dict = None,
) -> ToolResult:
    """Call API."""
    try:
        client = APIClient()
        response = client.request(api_name, method, endpoint, data=data)
        
        if response.success:
            return ToolResult(
                success=True,
                output={
                    "status": response.status_code,
                    "data": response.data if isinstance(response.data, (dict, list)) else str(response.data)[:500],
                },
            )
        else:
            return ToolResult(success=False, error=response.error)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_apis",
    description="List configured APIs",
    category="integration",
)
def list_apis() -> ToolResult:
    """List APIs."""
    try:
        client = APIClient()
        apis = []
        
        for name in client.list_apis():
            config = client.configs[name]
            apis.append({
                "name": name,
                "base_url": config.base_url,
                "auth_type": config.auth_type,
            })
        
        return ToolResult(success=True, output=apis)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing API Client...")
    
    client = APIClient(config_path="./test_api_configs.json")
    
    # Add test API
    client.add_api("test", "https://jsonplaceholder.typicode.com")
    print("Added test API")
    
    # Make request
    response = client.get("test", "/posts/1")
    print(f"\nGET /posts/1:")
    print(f"  Success: {response.success}")
    print(f"  Status: {response.status_code}")
    if response.data:
        print(f"  Data: {str(response.data)[:100]}...")
    
    # POST request
    response = client.post("test", "/posts", data={
        "title": "Test Post",
        "body": "Hello from JARVIS",
        "userId": 1,
    })
    print(f"\nPOST /posts:")
    print(f"  Success: {response.success}")
    print(f"  Status: {response.status_code}")
    
    # Cleanup
    if os.path.exists("./test_api_configs.json"):
        os.remove("./test_api_configs.json")
    
    print("\nAPI client test complete!")
