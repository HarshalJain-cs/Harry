"""
JARVIS Context Manager - Contextual awareness and RAG.

Provides retrieval-augmented generation and context tracking.
"""

import os
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


@dataclass
class ContextItem:
    """A piece of context information."""
    id: str
    content: str
    source: str
    type: str  # file, url, note, command, etc.
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class RetrievalResult:
    """Result from context retrieval."""
    items: List[ContextItem]
    query: str
    scores: List[float]


class ContextManager:
    """
    Manage contextual information for improved AI responses.
    
    Features:
    - Active window context
    - Recent commands/results
    - File context from open files
    - Semantic search over knowledge base
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/context",
        max_context_items: int = 20,
    ):
        """
        Initialize context manager.
        
        Args:
            storage_path: Path for persistence
            max_context_items: Maximum context items to maintain
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_items = max_context_items
        self.active_context: List[ContextItem] = []
        
        self._load()
    
    def _load(self):
        """Load persisted context."""
        context_file = self.storage_path / "active_context.json"
        if context_file.exists():
            try:
                with open(context_file, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    self.active_context.append(ContextItem(**item))
            except Exception:
                pass
    
    def _save(self):
        """Save context to disk."""
        context_file = self.storage_path / "active_context.json"
        
        data = []
        for item in self.active_context:
            data.append({
                "id": item.id,
                "content": item.content,
                "source": item.source,
                "type": item.type,
                "timestamp": item.timestamp.isoformat(),
                "metadata": item.metadata,
            })
        
        with open(context_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add(
        self,
        content: str,
        source: str,
        type: str = "general",
        metadata: Dict = None,
    ) -> ContextItem:
        """Add item to active context."""
        item = ContextItem(
            id=f"ctx_{datetime.now().timestamp()}",
            content=content[:2000],  # Truncate
            source=source,
            type=type,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        
        self.active_context.append(item)
        
        # Trim if needed
        if len(self.active_context) > self.max_items:
            self.active_context = self.active_context[-self.max_items:]
        
        self._save()
        return item
    
    def get_recent(self, count: int = 10, type: str = None) -> List[ContextItem]:
        """Get recent context items."""
        items = self.active_context
        if type:
            items = [i for i in items if i.type == type]
        return items[-count:]
    
    def clear(self):
        """Clear active context."""
        self.active_context.clear()
        self._save()
    
    def to_prompt_context(self, max_tokens: int = 1500) -> str:
        """Convert context to text for LLM prompt."""
        lines = []
        total_length = 0
        
        for item in reversed(self.active_context):
            line = f"[{item.type}] {item.content[:200]}"
            if total_length + len(line) > max_tokens:
                break
            lines.append(line)
            total_length += len(line)
        
        return "\n".join(reversed(lines))


class RAGSystem:
    """
    Retrieval-Augmented Generation system.
    
    Features:
    - Index documents/notes
    - Semantic search
    - Context injection
    """
    
    COLLECTION_NAME = "jarvis_knowledge"
    
    def __init__(
        self,
        storage_path: str = "./storage/rag",
    ):
        """
        Initialize RAG system.
        
        Args:
            storage_path: Path for ChromaDB storage
        """
        if not CHROMA_AVAILABLE:
            raise RuntimeError("ChromaDB not installed")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.storage_path),
        ))
        
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    
    def add_document(
        self,
        content: str,
        source: str,
        doc_type: str = "document",
        metadata: Dict = None,
    ) -> str:
        """
        Add a document to the knowledge base.
        
        Args:
            content: Document content
            source: Source identifier
            doc_type: Type of document
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        doc_id = f"doc_{datetime.now().timestamp()}"
        
        self.collection.add(
            documents=[content],
            ids=[doc_id],
            metadatas=[{
                "source": source,
                "type": doc_type,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {}),
            }],
        )
        
        return doc_id
    
    def add_file(self, file_path: str) -> Optional[str]:
        """Add file content to knowledge base."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.add_document(
                content=content[:10000],  # Limit size
                source=file_path,
                doc_type="file",
                metadata={"filename": os.path.basename(file_path)},
            )
        except Exception:
            return None
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        doc_type: str = None,
    ) -> RetrievalResult:
        """
        Search the knowledge base.
        
        Args:
            query: Search query
            n_results: Number of results
            doc_type: Filter by type
            
        Returns:
            RetrievalResult with matching items
        """
        where = None
        if doc_type:
            where = {"type": doc_type}
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        
        items = []
        scores = []
        
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                
                items.append(ContextItem(
                    id=results["ids"][0][i],
                    content=doc,
                    source=meta.get("source", "unknown"),
                    type=meta.get("type", "document"),
                    timestamp=datetime.now(),
                    metadata=meta,
                ))
                
                if results["distances"] and results["distances"][0]:
                    scores.append(1 - results["distances"][0][i])
                else:
                    scores.append(0.5)
        
        return RetrievalResult(
            items=items,
            query=query,
            scores=scores,
        )
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except:
            return False
    
    def get_augmented_prompt(
        self,
        query: str,
        max_context: int = 3,
    ) -> str:
        """
        Get query augmented with relevant context.
        
        Args:
            query: User query
            max_context: Maximum context items
            
        Returns:
            Augmented prompt string
        """
        results = self.search(query, n_results=max_context)
        
        if not results.items:
            return query
        
        context_lines = []
        for item in results.items:
            context_lines.append(f"[{item.source}]:\n{item.content[:500]}")
        
        augmented = f"""Based on this context:

{chr(10).join(context_lines)}

Answer this query: {query}"""
        
        return augmented


from tools.registry import tool, ToolResult


@tool(
    name="add_knowledge",
    description="Add information to the knowledge base for future reference",
    category="memory",
)
def add_knowledge(content: str, source: str = "user") -> ToolResult:
    """Add to knowledge base."""
    try:
        if not CHROMA_AVAILABLE:
            return ToolResult(success=False, error="ChromaDB not available")
        
        rag = RAGSystem()
        doc_id = rag.add_document(content, source)
        
        return ToolResult(
            success=True,
            output=f"Added to knowledge base: {doc_id}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_knowledge",
    description="Search the knowledge base for relevant information",
    category="memory",
)
def search_knowledge(query: str, limit: int = 5) -> ToolResult:
    """Search knowledge base."""
    try:
        if not CHROMA_AVAILABLE:
            return ToolResult(success=False, error="ChromaDB not available")
        
        rag = RAGSystem()
        results = rag.search(query, n_results=limit)
        
        items = [
            {
                "source": i.source,
                "preview": i.content[:100],
                "score": results.scores[idx],
            }
            for idx, i in enumerate(results.items)
        ]
        
        return ToolResult(success=True, output=items)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_context",
    description="Get current conversation context",
    category="memory",
)
def get_context() -> ToolResult:
    """Get active context."""
    try:
        ctx = ContextManager()
        recent = ctx.get_recent(10)
        
        items = [
            {
                "type": i.type,
                "source": i.source,
                "preview": i.content[:50],
            }
            for i in recent
        ]
        
        return ToolResult(success=True, output=items)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Context Manager...")
    
    # Test context manager
    ctx = ContextManager(storage_path="./test_context")
    
    ctx.add("User opened VSCode", "system", "app_switch")
    ctx.add("User asked about Python", "user", "command")
    ctx.add("Found 5 Python tutorials", "jarvis", "result")
    
    print("\nRecent context:")
    for item in ctx.get_recent(5):
        print(f"  [{item.type}] {item.content}")
    
    print(f"\nAs prompt:\n{ctx.to_prompt_context()}")
    
    # Test RAG if available
    if CHROMA_AVAILABLE:
        print("\n\nTesting RAG System...")
        
        rag = RAGSystem(storage_path="./test_rag")
        
        # Add documents
        rag.add_document("Python is a programming language", "test", "note")
        rag.add_document("JavaScript is used for web development", "test", "note")
        
        # Search
        results = rag.search("programming", n_results=2)
        print(f"\nSearch results for 'programming':")
        for i, item in enumerate(results.items):
            print(f"  {item.content[:50]}... (score: {results.scores[i]:.2f})")
    else:
        print("\nChromaDB not available, skipping RAG tests")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_context"):
        shutil.rmtree("./test_context")
    if os.path.exists("./test_rag"):
        shutil.rmtree("./test_rag")
    
    print("\nContext system test complete!")
