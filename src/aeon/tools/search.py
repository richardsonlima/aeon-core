
from typing import Dict, Any, List, Optional
from ddgs import DDGS
from aeon.tools.base import BaseTool

class SearchTool(BaseTool):
    """
    Search Tool using DuckDuckGo Search (ddgs).
    Provides web search capabilities to the agent.
    """
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information using DuckDuckGo. Useful for finding real-time info or general knowledge."
        )

    async def execute(self, query: str, max_results: int = 5) -> str:
        """
        Executes a web search query.
        """
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                
                if not results:
                    return f"No results found for query: {query}"
                
                output = []
                for idx, r in enumerate(results, 1):
                    output.append(f"{idx}. {r['title']}\n   URL: {r['href']}\n   Snippet: {r['body']}")
                
                return "\n\n".join(output)
        except Exception as e:
            return f"Search Error: {str(e)}"
