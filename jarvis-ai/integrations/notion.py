"""
JARVIS Notion Integration - Sync with Notion workspace.

Connects to Notion API for:
- Page management
- Database queries
- Content creation
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class NotionPage:
    """A Notion page."""
    id: str
    title: str
    url: str
    parent_type: str
    created_time: datetime
    last_edited: datetime
    properties: Dict[str, Any]


@dataclass
class NotionBlock:
    """A block in a Notion page."""
    id: str
    type: str
    content: str


class NotionClient:
    """
    Client for Notion API.
    
    Features:
    - Page CRUD operations
    - Database queries
    - Block manipulation
    - Search functionality
    """
    
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(self, token: str = None):
        """
        Initialize Notion client.
        
        Args:
            token: Notion integration token (from env if not provided)
        """
        self.token = token or os.environ.get("NOTION_TOKEN")
        self._client = None
        
        if not HTTPX_AVAILABLE:
            print("Warning: httpx not installed. Run: pip install httpx")
    
    def _get_client(self):
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    def is_configured(self) -> bool:
        """Check if Notion is properly configured."""
        return bool(self.token) and HTTPX_AVAILABLE
    
    def search_pages(self, query: str, limit: int = 10) -> List[NotionPage]:
        """
        Search for pages in workspace.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching NotionPage objects
        """
        if not self.is_configured():
            return []
        
        try:
            response = self._get_client().post(
                "/search",
                json={
                    "query": query,
                    "filter": {"property": "object", "value": "page"},
                    "page_size": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            pages = []
            for result in data.get("results", []):
                pages.append(self._parse_page(result))
            return pages
            
        except Exception as e:
            print(f"Notion search error: {e}")
            return []
    
    def get_page(self, page_id: str) -> Optional[NotionPage]:
        """Get a page by ID."""
        if not self.is_configured():
            return None
        
        try:
            response = self._get_client().get(f"/pages/{page_id}")
            response.raise_for_status()
            return self._parse_page(response.json())
        except Exception as e:
            print(f"Error getting page: {e}")
            return None
    
    def create_page(
        self,
        parent_id: str,
        title: str,
        content: str = None,
        parent_type: str = "page_id",
    ) -> Optional[NotionPage]:
        """
        Create a new page.
        
        Args:
            parent_id: Parent page or database ID
            title: Page title
            content: Optional page content
            parent_type: "page_id" or "database_id"
            
        Returns:
            Created NotionPage or None
        """
        if not self.is_configured():
            return None
        
        payload = {
            "parent": {parent_type: parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
        }
        
        # Add content as a paragraph block
        if content:
            payload["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ]
        
        try:
            response = self._get_client().post("/pages", json=payload)
            response.raise_for_status()
            return self._parse_page(response.json())
        except Exception as e:
            print(f"Error creating page: {e}")
            return None
    
    def append_to_page(self, page_id: str, content: str) -> bool:
        """Append content to a page."""
        if not self.is_configured():
            return False
        
        payload = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ]
        }
        
        try:
            response = self._get_client().patch(
                f"/blocks/{page_id}/children",
                json=payload,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error appending to page: {e}")
            return False
    
    def query_database(
        self,
        database_id: str,
        filter_obj: Dict = None,
        limit: int = 10,
    ) -> List[NotionPage]:
        """Query a Notion database."""
        if not self.is_configured():
            return []
        
        payload = {"page_size": limit}
        if filter_obj:
            payload["filter"] = filter_obj
        
        try:
            response = self._get_client().post(
                f"/databases/{database_id}/query",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            return [self._parse_page(r) for r in data.get("results", [])]
        except Exception as e:
            print(f"Error querying database: {e}")
            return []
    
    def _parse_page(self, data: Dict) -> NotionPage:
        """Parse API response to NotionPage."""
        # Extract title from properties
        title = "Untitled"
        props = data.get("properties", {})
        
        for key, value in props.items():
            if value.get("type") == "title":
                title_arr = value.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "Untitled")
                break
        
        parent = data.get("parent", {})
        parent_type = parent.get("type", "unknown")
        
        return NotionPage(
            id=data.get("id", ""),
            title=title,
            url=data.get("url", ""),
            parent_type=parent_type,
            created_time=datetime.fromisoformat(
                data.get("created_time", datetime.now().isoformat()).replace("Z", "+00:00")
            ),
            last_edited=datetime.fromisoformat(
                data.get("last_edited_time", datetime.now().isoformat()).replace("Z", "+00:00")
            ),
            properties=props,
        )
    
    def close(self):
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton
_notion_client: Optional[NotionClient] = None


def get_notion_client() -> NotionClient:
    """Get or create Notion client singleton."""
    global _notion_client
    if _notion_client is None:
        _notion_client = NotionClient()
    return _notion_client


# Tool registrations
from tools.registry import tool, ToolResult


@tool(
    name="notion_search",
    description="Search for pages in Notion workspace",
    category="integrations",
    examples=["search notion for meeting notes", "find in notion project plan"],
)
def notion_search(query: str, limit: int = 5) -> ToolResult:
    """Search Notion pages."""
    client = get_notion_client()
    
    if not client.is_configured():
        return ToolResult(
            success=False,
            error="Notion not configured. Set NOTION_TOKEN environment variable.",
        )
    
    pages = client.search_pages(query, limit)
    
    if not pages:
        return ToolResult(success=True, output=f"No pages found for '{query}'")
    
    output = [f"Found {len(pages)} page(s):"]
    for page in pages:
        output.append(f"  • {page.title}")
    
    return ToolResult(success=True, output="\n".join(output))


@tool(
    name="notion_create_page",
    description="Create a new page in Notion",
    category="integrations",
    examples=["create notion page meeting notes", "new notion page project ideas"],
)
def notion_create_page(
    title: str,
    content: str = None,
    parent_id: str = None,
) -> ToolResult:
    """Create a Notion page."""
    client = get_notion_client()
    
    if not client.is_configured():
        return ToolResult(
            success=False,
            error="Notion not configured. Set NOTION_TOKEN environment variable.",
        )
    
    if not parent_id:
        return ToolResult(
            success=False,
            error="Parent page or database ID required.",
        )
    
    page = client.create_page(parent_id, title, content)
    
    if page:
        return ToolResult(
            success=True,
            output=f"Created page: {page.title}\nURL: {page.url}",
        )
    return ToolResult(success=False, error="Failed to create page")


if __name__ == "__main__":
    print("Testing Notion Integration...")
    
    client = NotionClient()
    
    if client.is_configured():
        print("Notion configured!")
        pages = client.search_pages("test", limit=3)
        print(f"Found {len(pages)} pages")
    else:
        print("Notion not configured. Set NOTION_TOKEN environment variable.")
    
    print("\nNotion integration test complete!")
