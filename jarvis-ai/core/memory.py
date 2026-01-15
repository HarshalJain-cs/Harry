"""
JARVIS Memory System - Persistent storage and semantic search.

Provides:
- SQLite for structured data (commands, context, preferences)
- ChromaDB for semantic vector search (memories, documents)
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


@dataclass
class Memory:
    """A memory entry."""
    id: str
    content: str
    memory_type: str
    metadata: Dict[str, Any]
    timestamp: datetime
    score: float = 1.0  # Relevance score for search results


class MemorySystem:
    """
    Hybrid memory system combining SQL and vector storage.
    
    SQLite handles:
    - Command history
    - User context/preferences
    - Skill proficiency tracking
    - Session state
    
    ChromaDB handles:
    - Semantic memory search
    - Document/knowledge storage
    - Conversation history embedding
    """
    
    def __init__(
        self,
        db_path: str = "./storage/jarvis.db",
        chroma_path: str = "./storage/chroma",
    ):
        """
        Initialize memory system.
        
        Args:
            db_path: Path to SQLite database
            chroma_path: Path to ChromaDB storage
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        
        # Ensure directories exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_sqlite()
        
        # Initialize ChromaDB
        self.chroma_client = None
        self.memories_collection = None
        if CHROMA_AVAILABLE:
            self._init_chroma()
    
    def _init_sqlite(self):
        """Initialize SQLite tables."""
        self.conn.executescript("""
            -- Command history
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                intent TEXT,
                entities TEXT,
                success INTEGER,
                execution_time REAL,
                error TEXT
            );
            
            -- User context/preferences
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- User skill proficiency
            CREATE TABLE IF NOT EXISTS skills (
                domain TEXT PRIMARY KEY,
                proficiency REAL DEFAULT 0.5,
                interaction_count INTEGER DEFAULT 0,
                last_used TEXT
            );
            
            -- Session state
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                command_count INTEGER DEFAULT 0,
                context TEXT
            );
            
            -- Clipboard history
            CREATE TABLE IF NOT EXISTS clipboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                timestamp TEXT NOT NULL,
                source_app TEXT
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_commands_timestamp ON commands(timestamp);
            CREATE INDEX IF NOT EXISTS idx_commands_intent ON commands(intent);
        """)
        self.conn.commit()
    
    def _init_chroma(self):
        """Initialize ChromaDB for semantic search."""
        try:
            self.chroma_client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.chroma_path,
                anonymized_telemetry=False,
            ))
            
            self.memories_collection = self.chroma_client.get_or_create_collection(
                name="jarvis_memories",
                metadata={"description": "JARVIS semantic memories"}
            )
        except Exception as e:
            print(f"ChromaDB initialization failed: {e}")
            self.chroma_client = None
    
    # ===== Command History =====
    
    def log_command(
        self,
        command: str,
        intent: str,
        entities: Dict = None,
        success: bool = True,
        execution_time: float = 0.0,
        error: str = None,
    ):
        """Log a command execution."""
        import json
        
        self.conn.execute(
            """INSERT INTO commands 
               (timestamp, command, intent, entities, success, execution_time, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                command,
                intent,
                json.dumps(entities) if entities else None,
                1 if success else 0,
                execution_time,
                error,
            )
        )
        self.conn.commit()
    
    def get_recent_commands(self, limit: int = 10) -> List[Dict]:
        """Get recent command history."""
        import json
        
        cursor = self.conn.execute(
            """SELECT timestamp, command, intent, entities, success
               FROM commands ORDER BY id DESC LIMIT ?""",
            (limit,)
        )
        
        commands = []
        for row in cursor.fetchall():
            commands.append({
                "timestamp": row[0],
                "command": row[1],
                "intent": row[2],
                "entities": json.loads(row[3]) if row[3] else {},
                "success": bool(row[4]),
            })
        
        return commands
    
    def get_command_stats(self) -> Dict:
        """Get command usage statistics."""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(success) as successful,
                AVG(execution_time) as avg_time
            FROM commands
        """)
        row = cursor.fetchone()
        
        intent_cursor = self.conn.execute("""
            SELECT intent, COUNT(*) as count
            FROM commands
            WHERE intent IS NOT NULL
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 10
        """)
        
        return {
            "total_commands": row[0],
            "successful_commands": row[1],
            "success_rate": row[1] / row[0] if row[0] > 0 else 0,
            "avg_execution_time": row[2],
            "top_intents": dict(intent_cursor.fetchall()),
        }
    
    # ===== Context/Preferences =====
    
    def set_context(self, key: str, value: Any):
        """Set a context value."""
        import json
        
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        self.conn.execute(
            """INSERT OR REPLACE INTO context (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (key, value_str, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        import json
        
        cursor = self.conn.execute(
            "SELECT value FROM context WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return default
        
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return row[0]
    
    def delete_context(self, key: str):
        """Delete a context value."""
        self.conn.execute("DELETE FROM context WHERE key = ?", (key,))
        self.conn.commit()
    
    # ===== Semantic Memory (ChromaDB) =====
    
    def add_memory(
        self,
        content: str,
        memory_type: str = "general",
        metadata: Dict = None,
    ) -> str:
        """Add a semantic memory."""
        if not self.memories_collection:
            return ""
        
        memory_id = f"mem_{datetime.now().timestamp()}"
        
        meta = metadata or {}
        meta["type"] = memory_type
        meta["timestamp"] = datetime.now().isoformat()
        
        self.memories_collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[memory_id],
        )
        
        return memory_id
    
    def search_memories(
        self,
        query: str,
        n_results: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Memory]:
        """Search memories semantically."""
        if not self.memories_collection:
            return []
        
        where_filter = None
        if memory_type:
            where_filter = {"type": memory_type}
        
        results = self.memories_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )
        
        memories = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                memories.append(Memory(
                    id=results["ids"][0][i],
                    content=doc,
                    memory_type=meta.get("type", "general"),
                    metadata=meta,
                    timestamp=datetime.fromisoformat(
                        meta.get("timestamp", datetime.now().isoformat())
                    ),
                    score=1.0 - (results["distances"][0][i] if results["distances"] else 0),
                ))
        
        return memories
    
    def delete_memory(self, memory_id: str):
        """Delete a memory by ID."""
        if self.memories_collection:
            self.memories_collection.delete(ids=[memory_id])
    
    # ===== Clipboard History =====
    
    def save_clipboard(self, content: str, source_app: str = None):
        """Save clipboard content."""
        self.conn.execute(
            """INSERT INTO clipboard (content, timestamp, source_app)
               VALUES (?, ?, ?)""",
            (content, datetime.now().isoformat(), source_app)
        )
        self.conn.commit()
    
    def get_clipboard_history(self, limit: int = 20) -> List[Dict]:
        """Get clipboard history."""
        cursor = self.conn.execute(
            """SELECT content, timestamp, source_app
               FROM clipboard ORDER BY id DESC LIMIT ?""",
            (limit,)
        )
        
        return [
            {"content": row[0], "timestamp": row[1], "source": row[2]}
            for row in cursor.fetchall()
        ]
    
    def search_clipboard(self, query: str) -> List[Dict]:
        """Search clipboard history."""
        cursor = self.conn.execute(
            """SELECT content, timestamp FROM clipboard
               WHERE content LIKE ? ORDER BY id DESC LIMIT 20""",
            (f"%{query}%",)
        )
        
        return [
            {"content": row[0], "timestamp": row[1]}
            for row in cursor.fetchall()
        ]
    
    def close(self):
        """Close database connections."""
        self.conn.close()
        if self.chroma_client:
            self.chroma_client.persist()


if __name__ == "__main__":
    # Test memory system
    print("Testing Memory System...")
    
    memory = MemorySystem(
        db_path="./test_storage/test.db",
        chroma_path="./test_storage/chroma",
    )
    
    # Test command logging
    print("\nLogging commands...")
    memory.log_command("open chrome", "open_app", {"app": "chrome"}, True, 0.5)
    memory.log_command("search python", "web_search", {"query": "python"}, True, 1.2)
    
    print("Recent commands:")
    for cmd in memory.get_recent_commands(5):
        print(f"  - {cmd['command']} ({cmd['intent']})")
    
    # Test context
    print("\nTesting context...")
    memory.set_context("user_name", "Harry")
    memory.set_context("preferences", {"theme": "dark", "voice": "aria"})
    
    print(f"User name: {memory.get_context('user_name')}")
    print(f"Preferences: {memory.get_context('preferences')}")
    
    # Test semantic memory
    if CHROMA_AVAILABLE:
        print("\nTesting semantic memory...")
        memory.add_memory("User prefers dark mode and concise responses", "preference")
        memory.add_memory("User works in Python and JavaScript", "skill")
        
        results = memory.search_memories("What programming languages?")
        print(f"Search results: {len(results)}")
        for m in results:
            print(f"  - {m.content[:50]}... (score: {m.score:.2f})")
    
    memory.close()
    print("\nMemory system test complete.")
