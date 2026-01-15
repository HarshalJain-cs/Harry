"""
JARVIS Browser Automation - Web browser control and scraping.

Provides browser automation using Playwright for web interactions.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class PageInfo:
    """Information about a web page."""
    url: str
    title: str
    content_preview: str


class BrowserAutomation:
    """
    Automate web browser interactions.
    
    Features:
    - Navigate to URLs
    - Click elements
    - Type text
    - Extract content
    - Take page screenshots
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize browser automation.
        
        Args:
            headless: Run browser in headless mode
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")
        
        self.headless = headless
        self.browser = None
        self.page = None
        self._playwright = None
    
    async def start(self, browser_type: str = "chromium"):
        """Start the browser."""
        self._playwright = await async_playwright().start()
        
        if browser_type == "firefox":
            self.browser = await self._playwright.firefox.launch(headless=self.headless)
        elif browser_type == "webkit":
            self.browser = await self._playwright.webkit.launch(headless=self.headless)
        else:
            self.browser = await self._playwright.chromium.launch(headless=self.headless)
        
        self.page = await self.browser.new_page()
    
    async def stop(self):
        """Stop the browser."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def navigate(self, url: str, wait: bool = True) -> PageInfo:
        """Navigate to a URL."""
        if not self.page:
            await self.start()
        
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        await self.page.goto(url)
        
        if wait:
            await self.page.wait_for_load_state("domcontentloaded")
        
        title = await self.page.title()
        content = await self.page.content()
        
        # Get text preview
        text = await self.page.evaluate("document.body.innerText")
        preview = text[:500] if text else ""
        
        return PageInfo(
            url=self.page.url,
            title=title,
            content_preview=preview,
        )
    
    async def click(self, selector: str):
        """Click an element."""
        await self.page.click(selector)
    
    async def click_text(self, text: str):
        """Click element containing text."""
        await self.page.click(f"text={text}")
    
    async def type_text(self, selector: str, text: str):
        """Type text into an input."""
        await self.page.fill(selector, text)
    
    async def press_key(self, key: str):
        """Press a keyboard key."""
        await self.page.keyboard.press(key)
    
    async def scroll(self, direction: str = "down", amount: int = 500):
        """Scroll the page."""
        if direction == "down":
            await self.page.mouse.wheel(0, amount)
        elif direction == "up":
            await self.page.mouse.wheel(0, -amount)
    
    async def get_text(self, selector: Optional[str] = None) -> str:
        """Get text content from page or element."""
        if selector:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_text()
            return ""
        else:
            return await self.page.evaluate("document.body.innerText")
    
    async def get_links(self) -> List[Dict[str, str]]:
        """Get all links on page."""
        links = await self.page.evaluate("""
            Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.innerText.trim(),
                href: a.href
            })).filter(l => l.text && l.href)
        """)
        return links[:50]  # Limit results
    
    async def screenshot(self, path: str = "browser_screenshot.png"):
        """Take a screenshot of the page."""
        await self.page.screenshot(path=path)
        return path
    
    async def evaluate(self, script: str) -> Any:
        """Run JavaScript on the page."""
        return await self.page.evaluate(script)
    
    async def wait_for(self, selector: str, timeout: int = 5000):
        """Wait for an element to appear."""
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def extract_form_fields(self) -> List[Dict]:
        """Extract form fields from page."""
        fields = await self.page.evaluate("""
            Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                type: el.type || el.tagName.toLowerCase(),
                name: el.name,
                id: el.id,
                placeholder: el.placeholder
            })).filter(f => f.name || f.id)
        """)
        return fields


# Synchronous wrapper for tools
def _run_async(coro):
    """Run async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# Tool registrations
@tool(
    name="browse_url",
    description="Open a URL and get page content",
    category="automation",
    examples=["browse to wikipedia.org", "open example.com"],
)
def browse_url(url: str) -> ToolResult:
    """Browse to URL and get content."""
    async def _browse():
        browser = BrowserAutomation(headless=True)
        try:
            await browser.start()
            info = await browser.navigate(url)
            
            return {
                "url": info.url,
                "title": info.title,
                "preview": info.content_preview[:1000],
            }
        finally:
            await browser.stop()
    
    try:
        result = _run_async(_browse())
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="scrape_page",
    description="Extract text content from a web page",
    category="automation",
)
def scrape_page(url: str) -> ToolResult:
    """Scrape page text content."""
    async def _scrape():
        browser = BrowserAutomation(headless=True)
        try:
            await browser.start()
            await browser.navigate(url)
            text = await browser.get_text()
            
            return text[:5000] + ("..." if len(text) > 5000 else "")
        finally:
            await browser.stop()
    
    try:
        result = _run_async(_scrape())
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_page_links",
    description="Get all links from a web page",
    category="automation",
)
def get_page_links(url: str) -> ToolResult:
    """Get links from page."""
    async def _get_links():
        browser = BrowserAutomation(headless=True)
        try:
            await browser.start()
            await browser.navigate(url)
            links = await browser.get_links()
            
            return [
                {"text": l["text"][:50], "href": l["href"]}
                for l in links[:20]
            ]
        finally:
            await browser.stop()
    
    try:
        result = _run_async(_get_links())
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="fill_form",
    description="Fill out a form on a web page",
    risk_level=RiskLevel.MEDIUM,
    category="automation",
)
def fill_form(url: str, fields: Dict[str, str]) -> ToolResult:
    """Fill form fields."""
    async def _fill():
        browser = BrowserAutomation(headless=True)
        try:
            await browser.start()
            await browser.navigate(url)
            
            for selector, value in fields.items():
                await browser.type_text(selector, value)
            
            return f"Filled {len(fields)} fields"
        finally:
            await browser.stop()
    
    try:
        result = _run_async(_fill())
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="browser_screenshot",
    description="Take a screenshot of a web page",
    category="automation",
)
def browser_screenshot(url: str, path: Optional[str] = None) -> ToolResult:
    """Screenshot web page."""
    from datetime import datetime
    
    if not path:
        path = f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    async def _screenshot():
        browser = BrowserAutomation(headless=True)
        try:
            await browser.start()
            await browser.navigate(url)
            await browser.screenshot(path)
            return path
        finally:
            await browser.stop()
    
    try:
        result = _run_async(_screenshot())
        return ToolResult(success=True, output=f"Screenshot saved: {result}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Browser Automation...")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available")
        print("Install with: pip install playwright && playwright install")
    else:
        async def test():
            browser = BrowserAutomation(headless=True)
            try:
                await browser.start()
                
                # Navigate
                info = await browser.navigate("https://example.com")
                print(f"Title: {info.title}")
                print(f"URL: {info.url}")
                print(f"Preview: {info.content_preview[:100]}...")
                
                # Get links
                links = await browser.get_links()
                print(f"Links: {len(links)}")
                
            finally:
                await browser.stop()
        
        try:
            _run_async(test())
        except Exception as e:
            print(f"Test failed: {e}")
    
    print("\nTests complete!")
