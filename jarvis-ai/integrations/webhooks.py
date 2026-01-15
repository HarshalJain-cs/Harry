"""
JARVIS Webhook Manager - Incoming webhook handling.

Receives and processes webhooks from external services.
"""

import os
import json
import hmac
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


@dataclass
class WebhookEvent:
    """A received webhook event."""
    id: str
    source: str
    event_type: str
    payload: Dict[str, Any]
    received_at: datetime
    signature_valid: Optional[bool] = None


@dataclass
class WebhookConfig:
    """Webhook endpoint configuration."""
    name: str
    path: str
    secret: Optional[str] = None  # For signature verification
    handler: Optional[str] = None  # Tool/action to run


class WebhookManager:
    """
    Manage incoming webhooks.
    
    Features:
    - Register webhook endpoints
    - Signature verification
    - Event logging
    - Action triggers
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/webhooks",
        host: str = "localhost",
        port: int = 8765,
    ):
        """
        Initialize webhook manager.
        
        Args:
            storage_path: Path for webhook data
            host: Server host
            port: Server port
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.host = host
        self.port = port
        
        self.endpoints: Dict[str, WebhookConfig] = {}
        self.events: List[WebhookEvent] = []
        self.handlers: Dict[str, Callable] = {}
        
        self._server = None
        self._server_thread = None
        
        self._load()
    
    def _load(self):
        """Load webhook configurations."""
        config_file = self.storage_path / "webhooks.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                for name, config in data.get("endpoints", {}).items():
                    self.endpoints[name] = WebhookConfig(**config)
            except Exception:
                pass
    
    def _save(self):
        """Save configurations."""
        config_file = self.storage_path / "webhooks.json"
        
        data = {
            "endpoints": {
                name: asdict(config)
                for name, config in self.endpoints.items()
            },
        }
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_endpoint(
        self,
        name: str,
        path: str,
        secret: str = None,
        handler: str = None,
    ) -> WebhookConfig:
        """
        Register a webhook endpoint.
        
        Args:
            name: Endpoint name
            path: URL path (e.g., /github)
            secret: Verification secret
            handler: Tool to run on event
            
        Returns:
            WebhookConfig
        """
        config = WebhookConfig(
            name=name,
            path=path.lstrip('/'),
            secret=secret,
            handler=handler,
        )
        
        self.endpoints[name] = config
        self._save()
        
        return config
    
    def unregister_endpoint(self, name: str) -> bool:
        """Remove a webhook endpoint."""
        if name in self.endpoints:
            del self.endpoints[name]
            self._save()
            return True
        return False
    
    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        algorithm: str = "sha256",
    ) -> bool:
        """Verify webhook signature."""
        if not secret or not signature:
            return False
        
        expected = hmac.new(
            secret.encode(),
            payload,
            getattr(hashlib, algorithm),
        ).hexdigest()
        
        # Handle prefixed signatures (e.g., sha256=xxx)
        if '=' in signature:
            signature = signature.split('=', 1)[1]
        
        return hmac.compare_digest(expected, signature)
    
    def handle_event(
        self,
        path: str,
        payload: Dict,
        headers: Dict,
    ) -> WebhookEvent:
        """
        Process a webhook event.
        
        Args:
            path: Request path
            payload: Event payload
            headers: Request headers
            
        Returns:
            WebhookEvent
        """
        # Find matching endpoint
        endpoint = None
        for config in self.endpoints.values():
            if config.path == path.lstrip('/'):
                endpoint = config
                break
        
        event = WebhookEvent(
            id=f"evt_{datetime.now().timestamp()}",
            source=endpoint.name if endpoint else "unknown",
            event_type=headers.get("X-Event-Type", payload.get("type", "unknown")),
            payload=payload,
            received_at=datetime.now(),
        )
        
        # Verify signature if configured
        if endpoint and endpoint.secret:
            signature = headers.get("X-Hub-Signature-256") or headers.get("X-Signature")
            event.signature_valid = self.verify_signature(
                json.dumps(payload).encode(),
                signature or "",
                endpoint.secret,
            )
        
        # Log event
        self.events.append(event)
        if len(self.events) > 100:
            self.events = self.events[-100:]
        
        # Trigger handler if configured
        if endpoint and endpoint.handler and self.handlers.get(endpoint.handler):
            try:
                self.handlers[endpoint.handler](event)
            except Exception:
                pass
        
        return event
    
    def get_recent_events(self, limit: int = 20) -> List[WebhookEvent]:
        """Get recent webhook events."""
        return self.events[-limit:]
    
    def start_server(self):
        """Start the webhook server."""
        if self._server:
            return
        
        manager = self
        
        class WebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                
                try:
                    payload = json.loads(body.decode('utf-8'))
                except:
                    payload = {"raw": body.decode('utf-8', errors='replace')}
                
                headers = dict(self.headers)
                event = manager.handle_event(self.path, payload, headers)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response = {"received": event.id}
                self.wfile.write(json.dumps(response).encode())
            
            def log_message(self, *args):
                pass  # Suppress logging
        
        self._server = HTTPServer((self.host, self.port), WebhookHandler)
        
        def run():
            self._server.serve_forever()
        
        self._server_thread = threading.Thread(target=run, daemon=True)
        self._server_thread.start()
    
    def stop_server(self):
        """Stop the webhook server."""
        if self._server:
            self._server.shutdown()
            self._server = None
    
    def get_webhook_url(self, endpoint_name: str) -> str:
        """Get the full URL for a webhook endpoint."""
        if endpoint_name not in self.endpoints:
            return ""
        
        path = self.endpoints[endpoint_name].path
        return f"http://{self.host}:{self.port}/{path}"


from tools.registry import tool, ToolResult


@tool(
    name="register_webhook",
    description="Register a webhook endpoint",
    category="integration",
)
def register_webhook(name: str, path: str, secret: str = None) -> ToolResult:
    """Register webhook."""
    try:
        manager = WebhookManager()
        config = manager.register_endpoint(name, path, secret)
        url = manager.get_webhook_url(name)
        
        return ToolResult(
            success=True,
            output={
                "name": name,
                "path": config.path,
                "url": url,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_webhooks",
    description="List registered webhooks",
    category="integration",
)
def list_webhooks() -> ToolResult:
    """List webhooks."""
    try:
        manager = WebhookManager()
        
        webhooks = [
            {
                "name": config.name,
                "path": config.path,
                "has_secret": bool(config.secret),
            }
            for config in manager.endpoints.values()
        ]
        
        return ToolResult(success=True, output=webhooks)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="recent_webhook_events",
    description="Show recent webhook events",
    category="integration",
)
def recent_webhook_events(limit: int = 10) -> ToolResult:
    """Get recent events."""
    try:
        manager = WebhookManager()
        events = manager.get_recent_events(limit)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "id": e.id,
                    "source": e.source,
                    "type": e.event_type,
                    "received": e.received_at.isoformat(),
                }
                for e in events
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Webhook Manager...")
    
    manager = WebhookManager(storage_path="./test_webhooks")
    
    # Register endpoint
    config = manager.register_endpoint("github", "/github", secret="mysecret123")
    print(f"Registered: {config.name} at /{config.path}")
    
    # Simulate event
    event = manager.handle_event(
        "/github",
        {"action": "push", "repository": "test/repo"},
        {"X-Event-Type": "push", "X-Hub-Signature-256": "sha256=..."},
    )
    print(f"Event: {event.id} - {event.event_type}")
    
    # Get recent events
    events = manager.get_recent_events(5)
    print(f"Recent events: {len(events)}")
    
    # Get webhook URL
    url = manager.get_webhook_url("github")
    print(f"Webhook URL: {url}")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_webhooks"):
        shutil.rmtree("./test_webhooks")
    
    print("\nWebhook test complete!")
