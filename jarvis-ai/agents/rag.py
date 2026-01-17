"""
JARVIS RAG Agent - Retrieval-Augmented Generation
=================================================

Enables document ingestion and semantic search across knowledge base.
Uses ChromaDB for vector storage and sentence-transformers for embeddings.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


@dataclass
class Document:
    """Represents an ingested document."""
    id: str
    filename: str
    filepath: str
    content: str
    chunks: List[str]
    metadata: Dict[str, Any]
    ingested_at: str


@dataclass
class SearchResult:
    """Result from knowledge base search."""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]


class RAGAgent:
    """
    RAG (Retrieval-Augmented Generation) Agent.
    
    Provides document ingestion and semantic search capabilities.
    
    Usage:
        rag = RAGAgent()
        rag.ingest_document("path/to/doc.pdf")
        results = rag.query("What is the main topic?")
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        Initialize RAG Agent.
        
        Args:
            storage_path: Path to store ChromaDB data
            embedding_model: Sentence transformer model name
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embeddings
        self._embedder = None
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB
        self._client = None
        self._collection = None
        
        # Document index
        self.documents: Dict[str, Document] = {}
        self._load_document_index()
    
    @property
    def embedder(self):
        """Lazy-load embedder."""
        if self._embedder is None:
            if EMBEDDINGS_AVAILABLE:
                self._embedder = SentenceTransformer(self.embedding_model)
            else:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
        return self._embedder
    
    @property
    def collection(self):
        """Lazy-load ChromaDB collection."""
        if self._collection is None:
            if CHROMA_AVAILABLE:
                self._client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(self.storage_path / "chroma"),
                    anonymized_telemetry=False
                ))
                self._collection = self._client.get_or_create_collection(
                    name="jarvis_knowledge",
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                raise ImportError(
                    "chromadb not installed. Run: pip install chromadb"
                )
        return self._collection
    
    def ingest_document(self, filepath: str) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge base.
        
        Args:
            filepath: Path to the document
            
        Returns:
            dict with success status and document info
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return {"success": False, "error": f"File not found: {filepath}"}
        
        # Check if already ingested
        doc_id = self._generate_doc_id(filepath)
        if doc_id in self.documents:
            return {
                "success": True,
                "message": "Document already ingested",
                "document_id": doc_id
            }
        
        # Parse document
        try:
            from tools.productivity.document_parser import DocumentParser
            parser = DocumentParser()
            content, metadata = parser.parse(str(filepath))
        except ImportError:
            # Fallback to basic parsing
            content = self._basic_parse(filepath)
            metadata = {"filename": filepath.name}
        
        if not content:
            return {"success": False, "error": "Could not extract content from document"}
        
        # Chunk the content
        chunks = self._chunk_text(content)
        
        # Create document record
        doc = Document(
            id=doc_id,
            filename=filepath.name,
            filepath=str(filepath.absolute()),
            content=content,
            chunks=chunks,
            metadata=metadata,
            ingested_at=datetime.now().isoformat()
        )
        
        # Generate embeddings and store in ChromaDB
        try:
            embeddings = self.embedder.encode(chunks).tolist()
            
            self.collection.add(
                documents=chunks,
                embeddings=embeddings,
                ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
                metadatas=[
                    {
                        "doc_id": doc_id,
                        "chunk_index": i,
                        "source": filepath.name
                    }
                    for i in range(len(chunks))
                ]
            )
        except Exception as e:
            return {"success": False, "error": f"Embedding failed: {str(e)}"}
        
        # Save document record
        self.documents[doc_id] = doc
        self._save_document_index()
        
        return {
            "success": True,
            "document_id": doc_id,
            "filename": filepath.name,
            "chunks": len(chunks),
            "characters": len(content)
        }
    
    def ingest_directory(
        self,
        dir_path: str,
        extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ingest all documents in a directory.
        
        Args:
            dir_path: Path to directory
            extensions: List of file extensions to include (e.g., ['.pdf', '.txt'])
            
        Returns:
            dict with results for each file
        """
        dir_path = Path(dir_path)
        
        if not dir_path.is_dir():
            return {"success": False, "error": "Not a directory"}
        
        extensions = extensions or ['.txt', '.md', '.pdf', '.docx', '.json']
        results = []
        
        for file in dir_path.rglob("*"):
            if file.is_file() and file.suffix.lower() in extensions:
                result = self.ingest_document(str(file))
                results.append({
                    "file": file.name,
                    **result
                })
        
        return {
            "success": True,
            "processed": len(results),
            "results": results
        }
    
    def query(
        self,
        question: str,
        n_results: int = 5,
        include_sources: bool = True
    ) -> List[SearchResult]:
        """
        Query the knowledge base.
        
        Args:
            question: Natural language question
            n_results: Number of results to return
            include_sources: Whether to include source information
            
        Returns:
            List of SearchResult objects
        """
        # Generate query embedding
        query_embedding = self.embedder.encode([question]).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        search_results = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            search_results.append(SearchResult(
                content=doc,
                source=metadata.get('source', 'unknown'),
                score=1 - distance,  # Convert distance to similarity
                metadata=metadata
            ))
        
        return search_results
    
    def search_and_synthesize(
        self,
        question: str,
        n_results: int = 5
    ) -> str:
        """
        Search knowledge base and synthesize an answer using LLM.
        
        Args:
            question: Natural language question
            n_results: Number of context chunks to use
            
        Returns:
            Synthesized answer string
        """
        # Get relevant chunks
        results = self.query(question, n_results)
        
        if not results:
            return "I couldn't find relevant information in the knowledge base."
        
        # Build context
        context = "\n\n".join([
            f"[Source: {r.source}]\n{r.content}"
            for r in results
        ])
        
        # Use LLM to synthesize
        try:
            from ai.llm import get_llm_client
            llm = get_llm_client()
            
            prompt = f"""Based on the following context, answer the question.
If the context doesn't contain the answer, say so.

Context:
{context}

Question: {question}

Answer:"""
            
            response = llm.generate(prompt)
            return response.content
        except Exception as e:
            # Return raw results if LLM fails
            return f"Found {len(results)} relevant results:\n\n" + "\n\n".join([
                f"• {r.content[:200]}... (from {r.source})"
                for r in results
            ])
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all ingested documents."""
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "chunks": len(doc.chunks),
                "ingested_at": doc.ingested_at
            }
            for doc in self.documents.values()
        ]
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        if doc_id not in self.documents:
            return False
        
        doc = self.documents[doc_id]
        
        # Delete from ChromaDB
        chunk_ids = [f"{doc_id}_{i}" for i in range(len(doc.chunks))]
        try:
            self.collection.delete(ids=chunk_ids)
        except Exception:
            pass
        
        # Remove from index
        del self.documents[doc_id]
        self._save_document_index()
        
        return True
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        
        return [c for c in chunks if c]
    
    def _generate_doc_id(self, filepath: Path) -> str:
        """Generate unique document ID."""
        content = f"{filepath.absolute()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _basic_parse(self, filepath: Path) -> str:
        """Basic file parsing without external libraries."""
        suffix = filepath.suffix.lower()
        
        if suffix in ['.txt', '.md', '.json']:
            return filepath.read_text(encoding='utf-8', errors='ignore')
        
        return ""
    
    def _load_document_index(self):
        """Load document index from disk."""
        index_path = self.storage_path / "document_index.json"
        if index_path.exists():
            try:
                with open(index_path) as f:
                    data = json.load(f)
                    for doc_data in data:
                        doc = Document(**doc_data)
                        self.documents[doc.id] = doc
            except Exception:
                pass
    
    def _save_document_index(self):
        """Save document index to disk."""
        index_path = self.storage_path / "document_index.json"
        data = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "filepath": doc.filepath,
                "content": doc.content[:1000],  # Truncate for storage
                "chunks": doc.chunks,
                "metadata": doc.metadata,
                "ingested_at": doc.ingested_at
            }
            for doc in self.documents.values()
        ]
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2)


# Singleton instance
_rag_agent: Optional[RAGAgent] = None


def get_rag_agent() -> RAGAgent:
    """Get or create global RAG agent."""
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent


# Tool functions for registry
def ingest_document(filepath: str) -> Dict[str, Any]:
    """Ingest a document into the knowledge base."""
    return get_rag_agent().ingest_document(filepath)


def search_knowledge(query: str, n_results: int = 5) -> str:
    """Search the knowledge base and synthesize an answer."""
    return get_rag_agent().search_and_synthesize(query, n_results)


def list_knowledge() -> List[Dict[str, Any]]:
    """List all documents in the knowledge base."""
    return get_rag_agent().list_documents()
