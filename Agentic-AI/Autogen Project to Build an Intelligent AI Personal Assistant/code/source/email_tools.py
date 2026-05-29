import asyncio
from datetime import datetime
from typing import List, Union
import pytz
from autogen_ext.tools.langchain import LangChainToolAdapter
from autogen_core.tools import FunctionTool
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_resource_service as build_gmail_resource_service
from source.log_records import logger
from source.google_utils import get_gmail_service
from source.configurations import config

class GmailTools:
    """
    Class to handle Gmail tools creation using LangChain toolkit.
    
    Attributes:
        creds: Google API credentials
        default_timezone: Timezone for datetime operations
    """
    
    def __init__(self, creds):
        self.creds = creds
        self.default_timezone = config.DEFAULT_TIMEZONE

    async def get_current_datetime(self) -> str:
        """Get current date and time in the configured timezone."""
        try:
            tz = pytz.timezone(self.default_timezone)
            return datetime.now(tz).isoformat()
        except Exception as e:
            logger.error(f"Error getting current datetime: {str(e)}")
            # Fallback to UTC
            return datetime.now(pytz.UTC).isoformat()

    async def langchain_gmail_tools(self) -> List:
        """
        Create Gmail tools using LangChain toolkit.

        Returns:
            List of Gmail tools from LangChain toolkit
        """
        try:
            # Run in thread pool since build_resource_service might be blocking
            loop = asyncio.get_event_loop()
            api_resource = await loop.run_in_executor(
                None, 
                build_gmail_resource_service, 
                self.creds
            )
            gmail_toolkit = GmailToolkit(api_resource=api_resource)
            tools = gmail_toolkit.get_tools()
            logger.info(f"Created {len(tools)} Gmail tools from LangChain toolkit")
            return tools
        except Exception as e:
            logger.error(f"Error creating Gmail tools: {str(e)}")
            return []

    async def as_function_tools(self) -> List[Union[LangChainToolAdapter, FunctionTool]]:
        """
        Combine Gmail tools and utility tools for AutoGen agent.
        Gmail tools are wrapped in LangChainToolAdapter, utility functions use FunctionTool.

        Returns:
            List of tools for AutoGen (mix of LangChainToolAdapter and FunctionTool)
        """
        try:
            # Get Gmail tools and wrap them in LangChainToolAdapter
            gmail_tools = await self.langchain_gmail_tools()
            gmail_autogen_tools = [LangChainToolAdapter(tool) for tool in gmail_tools]
            
            # Create AutoGen FunctionTool for datetime function
            datetime_tool = FunctionTool(
                self.get_current_datetime,
                description="Get current date and time in ISO format"
            )
            
            # Combine all tools
            all_tools = gmail_autogen_tools + [datetime_tool]

            logger.info(f"Created {len(all_tools)} total tools for AutoGen agent ({len(gmail_autogen_tools)} Gmail tools + 1 utility tool)")
            return all_tools
            
        except Exception as e:
            logger.error(f"Error creating Gmail tools for AutoGen: {str(e)}")
            return []


# Function to create Gmail tools outside the class
async def create_gmail_tools(creds) -> List[Union[LangChainToolAdapter, FunctionTool]]:
    """
    Factory function to create Gmail tools for use outside the class.
    
    Args:
        creds: Google API credentials
        
    Returns:
        List of tools for AutoGen (mix of LangChainToolAdapter and FunctionTool)
    """
    gmail_tools_instance = GmailTools(creds)
    return await gmail_tools_instance.as_function_tools()


# Example usage:
    """Main test function."""
async def main():
    email_creds = get_gmail_service()
    email_tools = await create_gmail_tools(email_creds)
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
