"""
JARVIS Web Tools - Browser and internet tools.

Provides tools for web browsing, searching, and URL handling.
"""

import webbrowser
from typing import Optional
from urllib.parse import quote_plus

from tools.registry import tool, ToolResult, get_registry


@tool(
    name="open_website",
    description="Open a website in the default browser",
    category="web",
    examples=["open youtube", "go to github"],
)
def open_website(site: str) -> ToolResult:
    """Open a website."""
    try:
        # Add protocol if missing
        if not site.startswith(("http://", "https://")):
            # Check for common shortcuts
            shortcuts = {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "github": "https://github.com",
                "twitter": "https://twitter.com",
                "x": "https://x.com",
                "reddit": "https://reddit.com",
                "stackoverflow": "https://stackoverflow.com",
                "linkedin": "https://linkedin.com",
                "facebook": "https://facebook.com",
                "gmail": "https://mail.google.com",
                "drive": "https://drive.google.com",
                "docs": "https://docs.google.com",
                "sheets": "https://sheets.google.com",
                "netflix": "https://netflix.com",
                "spotify": "https://open.spotify.com",
                "amazon": "https://amazon.com",
            }
            
            site_lower = site.lower().strip()
            if site_lower in shortcuts:
                url = shortcuts[site_lower]
            else:
                url = f"https://{site}"
        else:
            url = site
        
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Opened {url}")
    
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_youtube",
    description="Search YouTube for videos",
    category="web",
    examples=["search youtube for music", "find tutorials on youtube"],
)
def search_youtube(query: str) -> ToolResult:
    """Search YouTube."""
    try:
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Searching YouTube for: {query}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_google",
    description="Search Google",
    category="web",
    examples=["google python tutorials", "search google for weather"],
)
def search_google(query: str) -> ToolResult:
    """Search Google."""
    try:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Searching Google for: {query}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_images",
    description="Search Google Images",
    category="web",
)
def search_images(query: str) -> ToolResult:
    """Search Google Images."""
    try:
        url = f"https://www.google.com/search?tbm=isch&q={quote_plus(query)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Searching images for: {query}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_maps",
    description="Search Google Maps for a location",
    category="web",
)
def search_maps(location: str) -> ToolResult:
    """Search Google Maps."""
    try:
        url = f"https://www.google.com/maps/search/{quote_plus(location)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Opening maps for: {location}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_weather",
    description="Get weather for a location",
    category="web",
)
def get_weather(location: Optional[str] = None) -> ToolResult:
    """Open weather for a location."""
    try:
        if location:
            url = f"https://www.google.com/search?q=weather+{quote_plus(location)}"
        else:
            url = "https://www.google.com/search?q=weather"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Opening weather for: {location or 'current location'}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="translate",
    description="Open Google Translate",
    category="web",
)
def translate(text: str, to_lang: str = "en") -> ToolResult:
    """Open Google Translate."""
    try:
        url = f"https://translate.google.com/?text={quote_plus(text)}&tl={to_lang}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Translating: {text[:50]}...")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_stack_overflow",
    description="Search Stack Overflow for programming help",
    category="web",
)
def search_stack_overflow(query: str) -> ToolResult:
    """Search Stack Overflow."""
    try:
        url = f"https://stackoverflow.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Searching Stack Overflow for: {query}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_github",
    description="Search GitHub for repositories",
    category="web",
)
def search_github(query: str) -> ToolResult:
    """Search GitHub."""
    try:
        url = f"https://github.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return ToolResult(success=True, output=f"Searching GitHub for: {query}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_time",
    description="Get current time",
    category="utility",
)
def get_time() -> ToolResult:
    """Get current time."""
    from datetime import datetime
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    
    return ToolResult(
        success=True,
        output={
            "time": time_str,
            "date": date_str,
            "full": f"It's {time_str} on {date_str}",
        }
    )


@tool(
    name="get_date",
    description="Get current date",
    category="utility",
)
def get_date() -> ToolResult:
    """Get current date."""
    from datetime import datetime
    now = datetime.now()
    
    return ToolResult(
        success=True,
        output={
            "date": now.strftime("%B %d, %Y"),
            "day": now.strftime("%A"),
            "year": now.year,
            "month": now.month,
            "day_of_month": now.day,
        }
    )


def register_web_tools():
    """Ensure all web tools are registered."""
    # Tools are auto-registered via decorators
    pass


if __name__ == "__main__":
    print("Testing Web Tools...")
    
    registry = get_registry()
    
    # Test get_time
    print("\nCurrent Time:")
    result = registry.execute("get_time", {})
    if result.success:
        print(f"  {result.output['full']}")
    
    # Test search (uncomment to actually open browser)
    # print("\nSearching YouTube...")
    # result = registry.execute("search_youtube", {"query": "Python tutorial"})
    # print(f"  {result.output}")
