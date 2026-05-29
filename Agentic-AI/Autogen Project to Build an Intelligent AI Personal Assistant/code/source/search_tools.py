import httpx
from datetime import datetime
from typing import Dict, Any, List
from autogen_core.tools import FunctionTool
from source.log_records import logger
from source.configurations import config
import pytz

class SearchTools:
    """Single class handling all search operations using Tavily API."""
    
    def __init__(self):
        self.tavily_api_key = config.TAVILY_SEARCH_KEY
        self.tavily_url = "https://api.tavily.com/search"
        self.default_max_results = config.MAX_RESULTS
        self.default_timezone = config.DEFAULT_TIMEZONE
        
    async def _make_tavily_request(self, query: str, search_depth: str = "basic", max_results: int = None) -> Dict[str, Any]:
        """Make request to Tavily search API."""
        if max_results is None:
            max_results = self.default_max_results
            
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
            "max_results": max_results,
            "include_images": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.tavily_url, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Tavily search completed for query: {query[:50]}...")
                return data
        except Exception as e:
            logger.error(f"Tavily API error for query '{query}': {str(e)}")
            raise
    
    def _format_search_results(self, data: Dict[str, Any], query: str) -> str:
        """Format search results into readable text."""
        try:
            results = []
            
            # Add answer if available
            answer = data.get("answer", "")
            if answer:
                results.append(f"Answer: {answer}\n")
            
            # Add search results
            search_results = data.get("results", [])
            if search_results:
                results.append("Search Results:")
                for i, result in enumerate(search_results, 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content")
                    
                    # Truncate content if too long
                    if len(content) > 200:
                        content = content[:200] + "..."
                    
                    results.append(f"\n{i}. {title}")
                    results.append(f"   URL: {url}")
                    results.append(f"   Summary: {content}")
            
            if not results:
                return f"No search results found for: {query}"
            
            formatted_result = "\n".join(results)
            logger.info(f"Formatted search results for query: {query[:50]}...")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error formatting search results: {str(e)}")
            return f"Error formatting search results: {str(e)}"
    
    # Public tool methods
    async def web_search(self, query: str) -> str:
        """Perform a web search and return formatted results."""
        try:
            if not query or not query.strip():
                return "Error: Search query cannot be empty"
            
            logger.info(f"Starting web search for: {query}")
            data = await self._make_tavily_request(query, search_depth="basic")
            result = self._format_search_results(data, query)
            logger.info(f"Web search completed for: {query[:50]}...")
            return result
            
        except Exception as e:
            error_msg = f"Error performing web search for '{query}': {str(e)}"
            logger.error(error_msg)
            return error_msg
    
        
    async def get_current_datetime(self) -> str:
        """Get current date and time in the configured timezone."""
        try:
            tz = pytz.timezone(self.default_timezone)
            return datetime.now(tz).isoformat()
        except Exception as e:
            logger.error(f"Error getting current datetime: {str(e)}")
            # Fallback to UTC
            return datetime.now(pytz.UTC).isoformat()
    
    async def research_search(self, topic: str) -> str:
        """Perform comprehensive research search on a topic."""
        try:
            if not topic or not topic.strip():
                return "Error: Research topic cannot be empty"
            
            logger.info(f"Starting research search for: {topic}")
            data = await self._make_tavily_request(topic, search_depth="advanced", max_results=10)
            
            # Enhanced formatting for research
            results = []
            answer = data.get("answer", "")
            if answer:
                results.append(f"Research Summary: {answer}\n")
            
            search_results = data.get("results", [])
            if search_results:
                results.append("Detailed Research Results:")
                for i, result in enumerate(search_results, 1):
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content")
                    
                    results.append(f"\n{i}. {title}")
                    results.append(f"   Source: {url}")
                    results.append(f"   Content: {content}")
                    results.append("   " + "-" * 80)
            
            if not results:
                return f"No research results found for: {topic}"
            
            formatted_result = "\n".join(results)
            logger.info(f"Research search completed for: {topic[:50]}...")
            return formatted_result
            
        except Exception as e:
            error_msg = f"Error performing research search for '{topic}': {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def as_function_tools(self) -> List[FunctionTool]:
        """Convert methods to FunctionTool instances for AutoGen."""
        tools = [
            FunctionTool(
                self.get_current_datetime,
                description="Get current date and time to understand temporal context for searches"
            ),
            FunctionTool(
                self.web_search,
                description="Perform a basic web search and return relevant results"
            ),
            FunctionTool(
                self.research_search,
                description="Perform comprehensive research search with detailed analysis"
            ),
        ]
        logger.info(f"Created {len(tools)} search function tools")
        return tools


# Usage function for creating search tools
def create_search_tools() -> List[FunctionTool]:
    """Create search tools using the single class approach."""
    search_tools = SearchTools()
    return search_tools.as_function_tools()


# Testing function
async def test_search_tools():
    """Test the search tools."""
    logger.info("Testing Search Tools")
    
    search = SearchTools()
    
    # Test basic web search
    logger.info("Testing web search")
    result = await search.web_search("What is Autogen?")
    logger.info(f"Web search result: {result[:200]}...")
    
    
    # Test function tools creation
    logger.info("Testing function tools creation")
    tools = await search.as_function_tools()
    logger.info(f"Created {len(tools)} tools: {[tool.name for tool in tools]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search_tools())