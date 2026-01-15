"""
JARVIS UI Server - Web interface for JARVIS.

Provides a FastAPI-based REST API and WebSocket for the frontend.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# ============ API Models ============

class CommandRequest(BaseModel):
    """Request for command execution."""
    command: str
    context: Optional[Dict[str, Any]] = None


class CommandResponse(BaseModel):
    """Response from command execution."""
    success: bool
    result: Optional[Any]
    error: Optional[str] = None
    execution_time: float = 0.0


class StatusResponse(BaseModel):
    """JARVIS status response."""
    status: str
    version: str
    uptime: float
    active_session: bool


# ============ WebSocket Manager ============

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


# ============ API Server ============

class JarvisAPI:
    """
    REST API and WebSocket server for JARVIS.
    
    Endpoints:
    - POST /command - Execute a command
    - GET /status - Get system status
    - GET /tools - List available tools
    - WS /ws - WebSocket for real-time updates
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI not installed. Run: pip install fastapi uvicorn")
        
        self.host = host
        self.port = port
        self.start_time = datetime.now()
        
        self.app = FastAPI(
            title="JARVIS API",
            version=self.VERSION,
            description="AI Operating Layer API",
        )
        
        self.manager = ConnectionManager()
        self.agent = None
        
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_middleware(self):
        """Configure CORS for frontend access."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Configure API routes."""
        
        @self.app.get("/", response_model=dict)
        async def root():
            return {"message": "JARVIS API", "version": self.VERSION}
        
        @self.app.get("/status", response_model=StatusResponse)
        async def get_status():
            uptime = (datetime.now() - self.start_time).total_seconds()
            return StatusResponse(
                status="running",
                version=self.VERSION,
                uptime=uptime,
                active_session=self.agent is not None,
            )
        
        @self.app.post("/command", response_model=CommandResponse)
        async def execute_command(request: CommandRequest):
            import time
            start = time.time()
            
            try:
                # Get or create agent
                if self.agent is None:
                    from core.agent import JarvisAgent
                    self.agent = JarvisAgent()
                
                # Process command
                result = await asyncio.to_thread(
                    self.agent.process_text,
                    request.command,
                )
                
                # Broadcast to WebSocket clients
                await self.manager.broadcast({
                    "type": "command_result",
                    "command": request.command,
                    "result": result.output if result else None,
                    "success": result.success if result else False,
                })
                
                return CommandResponse(
                    success=result.success if result else False,
                    result=result.output if result else None,
                    error=result.error if result and not result.success else None,
                    execution_time=time.time() - start,
                )
            
            except Exception as e:
                return CommandResponse(
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time=time.time() - start,
                )
        
        @self.app.get("/tools")
        async def list_tools():
            try:
                from tools.registry import get_registry
                registry = get_registry()
                
                tools = []
                for name, tool in registry.tools.items():
                    tools.append({
                        "name": name,
                        "description": tool.description,
                        "category": tool.category,
                        "risk_level": tool.risk_level.value,
                    })
                
                return {"tools": tools, "count": len(tools)}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/history")
        async def get_history(limit: int = 20):
            try:
                from core.memory import MemorySystem
                memory = MemorySystem()
                
                history = memory.get_command_history(limit)
                return {"history": history}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            
            await self.manager.send_personal(websocket, {
                "type": "connected",
                "message": "Connected to JARVIS",
            })
            
            try:
                while True:
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "command":
                        command = data.get("command", "")
                        
                        # Process command
                        if self.agent is None:
                            from core.agent import JarvisAgent
                            self.agent = JarvisAgent()
                        
                        result = await asyncio.to_thread(
                            self.agent.process_text,
                            command,
                        )
                        
                        await self.manager.send_personal(websocket, {
                            "type": "result",
                            "command": command,
                            "result": result.output if result else None,
                            "success": result.success if result else False,
                        })
                    
                    elif data.get("type") == "ping":
                        await self.manager.send_personal(websocket, {"type": "pong"})
            
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)
    
    def run(self):
        """Start the API server."""
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    async def run_async(self):
        """Start server asynchronously."""
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()


def create_app() -> FastAPI:
    """Create FastAPI app for production deployment."""
    api = JarvisAPI()
    return api.app


if __name__ == "__main__":
    print("Starting JARVIS API Server...")
    
    if not FASTAPI_AVAILABLE:
        print("FastAPI not available. Install with: pip install fastapi uvicorn")
    else:
        api = JarvisAPI(host="0.0.0.0", port=8080)
        print(f"\nServer running at http://localhost:8080")
        print("Endpoints:")
        print("  GET  /status  - System status")
        print("  POST /command - Execute command")
        print("  GET  /tools   - List tools")
        print("  WS   /ws      - WebSocket")
        print("\nPress Ctrl+C to stop")
        
        api.run()
