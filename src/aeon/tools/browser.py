import asyncio
import base64
from typing import Any, Dict, Optional, List
from aeon.tools.base import BaseTool

# Try to import playwright, but handle if not installed
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class BrowserTool(BaseTool):
    """
    Browser automation tool using Playwright.
    Allows the agent to navigate the web, extract content, and interact with pages.
    """
    
    def __init__(self, headless: bool = True):
        super().__init__(
            name="web_browser",
            description="Browse the web. Can navigate to URLs, extract text, click elements, fill forms, and take screenshots."
        )
        self.headless = headless
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "extract", "click", "type", "screenshot", "scroll"],
                    "description": "The action to perform on the page"
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (for 'navigate' action)"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for interaction (click/type/extract)"
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (for 'type' action)"
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Take full page screenshot (for 'screenshot' action)"
                }
            },
            "required": ["action"]
        }
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._playwright = None

    async def _ensure_browser(self):
        """Ensure the browser instance is running"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Please run 'pip install playwright' and 'playwright install'.")
            
        if not self._playwright:
            self._playwright = await async_playwright().start()
            
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            
        if not self._page:
            self._page = await self._browser.new_page()
            # Set a common user agent to avoid blocking
            await self._page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

    async def execute(self, **kwargs) -> Any:
        try:
            await self._ensure_browser()
            
            action = kwargs.get("action")
            
            if action == "navigate":
                url = kwargs.get("url")
                if not url:
                    return "Error: URL required for navigation"
                await self._page.goto(url, wait_until="domcontentloaded")
                title = await self._page.title()
                return f"Navigated to: {title} ({url})"
                
            elif action == "extract":
                selector = kwargs.get("selector", "body")
                if selector == "body":
                    # Extract readable text from the whole page
                    import io
                    from bs4 import BeautifulSoup
                    html = await self._page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text(separator=' ', strip=True)
                    # Limit output length to prevent context overflow
                    return text[:5000] + ("..." if len(text) > 5000 else "")
                else:
                    # Extract specific element text
                    element = await self._page.query_selector(selector)
                    if element:
                        return await element.inner_text()
                    return f"Element not found: {selector}"
                    
            elif action == "click":
                selector = kwargs.get("selector")
                if not selector:
                    return "Error: Selector required for click"
                await self._page.click(selector)
                return f"Clicked: {selector}"
                
            elif action == "type":
                selector = kwargs.get("selector")
                text = kwargs.get("text")
                if not selector or not text:
                    return "Error: Selector and text required for type"
                await self._page.fill(selector, text)
                return f"Typed '{text}' into {selector}"
                
            elif action == "screenshot":
                path = "screenshot.png"
                full_page = kwargs.get("full_page", False)
                await self._page.screenshot(path=path, full_page=full_page)
                return f"Screenshot saved to {path} (in current working directory)"
                
            elif action == "scroll":
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return "Scrolled to bottom of page"
                
            return f"Unknown action: {action}"
            
        except Exception as e:
            return f"Browser Error: {str(e)}"

    async def close(self):
        """Cleanup browser resources"""
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
