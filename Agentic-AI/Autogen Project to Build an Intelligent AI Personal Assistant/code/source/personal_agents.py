import asyncio
from typing import Dict
from zoneinfo import ZoneInfo
from tzlocal import get_localzone

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import configuration
from source.configurations import config

# Import the tools
from source.weather_tools import WeatherTools
from source.calendar_tools import CalendarTools
from source.email_tools import GmailTools
from source.search_tools import SearchTools
from source.google_utils import get_gmail_service
# Import prompts
from source.prompts import (
    email_system_prompt, 
    calendar_system_prompt, 
    weather_system_prompt,
    search_system_prompt,
    final_answer_prompt
)
from source.log_records import logger

def _get_timezone() -> ZoneInfo:
    """Get the current system timezone."""
    return ZoneInfo(str(get_localzone()))


def create_model_client() -> OpenAIChatCompletionClient:
    """Create and configure the OpenAI model client."""
    return OpenAIChatCompletionClient(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
        temperature=config.OPENAI_TEMPERATURE,
    )


async def create_email_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create and configure the email assistant agent."""
    try:
        email_creds = get_gmail_service()
        gmail_tools_instance = GmailTools(email_creds)
        email_tools = await gmail_tools_instance.as_function_tools()
        
        logger.info(f"Email tools created: {len(email_tools) if email_tools else 0}")
    except Exception as e:
        logger.warning(f"Email tools creation failed: {e}")
        email_tools = []
    
    return AssistantAgent(
        name="EmailAssistant",
        description="An AI assistant that helps you manage your email efficiently. Handles Gmail tasks: read, search, draft or send emails. Only pick me when the user explicitly wants email help.",
        model_client=model_client,
        tools=email_tools,
        system_message=email_system_prompt.format(timezone=str(_get_timezone())),
        reflect_on_tool_use=True,
    )


async def create_weather_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create and configure the weather assistant agent."""
    try:
        weather_tools_provider = WeatherTools()
        weather_tools = await weather_tools_provider.as_function_tools()
        logger.info(f"Weather tools created: {len(weather_tools) if weather_tools else 0}")
    except Exception as e:
        logger.warning(f"Weather tools creation failed: {e}")
        weather_tools = []
    
    return AssistantAgent(
        name="WeatherAssistant",
        description="An AI assistant that helps you get weather information. Answers questions about current weather, rain probability, or forecasts for any city. Pick me for queries like weather in Mumbai or will it rain tomorrow?",
        model_client=model_client,
        tools=weather_tools,
        system_message=weather_system_prompt.format(timezone=str(_get_timezone())),
        reflect_on_tool_use=True,
    )


async def create_calendar_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create and configure the calendar assistant agent."""
    try:
        calendar_tools_provider = CalendarTools()
        calendar_tools = await calendar_tools_provider.as_function_tools()
        logger.info(f"Calendar tools created: {len(calendar_tools) if calendar_tools else 0}")
    except Exception as e:
        logger.warning(f"Calendar tools creation failed: {e}")
        calendar_tools = []
    
    return AssistantAgent(
        name="CalendarAssistant",
        description="An AI assistant that helps you manage your calendar efficiently. Manages calendar events or availability. Use me for scheduling, moving, or listing meetings",
        model_client=model_client,
        tools=calendar_tools,
        system_message=calendar_system_prompt.format(timezone=str(_get_timezone())),
        reflect_on_tool_use=True,
    )


async def create_search_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create and configure the search assistant agent."""
    try:
        search_tools_provider = SearchTools()
        search_tools = await search_tools_provider.as_function_tools()
        logger.info(f"Search tools created: {len(search_tools) if search_tools else 0}")
    except Exception as e:
        logger.warning(f"Search tools creation failed: {e}")
        search_tools = []
    
    return AssistantAgent(
        name="SearchAssistant",
        description="An AI assistant that helps you find information on the web. Handles web searches, news searches, and research queries. Use me for finding current information, news, research, or any web-based queries.",
        model_client=model_client,
        tools=search_tools,
        system_message=search_system_prompt.format(timezone=str(_get_timezone())),
        reflect_on_tool_use=True,
    )


class PersonalAssistantOrchestrator:
    """
    Main orchestrator that manages multiple specialized agents and routes requests
    to the appropriate agent based on user input.
    """
    
    def __init__(self):
        """Initialize the orchestrator with configuration."""
        self.model_client = create_model_client()
        self.termination = TextMentionTermination("TERMINATE")
        
        # Initialize agents as None - they'll be created async
        self.email_agent = None
        self.weather_agent = None
        self.calendar_agent = None
        self.search_agent = None
        self.agent_list = None
        self.final_answer_prompt = final_answer_prompt
        
        # Context storage for multi-part queries
        self.conversation_context = {}
        
        # Flag to track if agents are initialized
        self._agents_initialized = False

    async def _initialize_agents(self):
        """Initialize all agents asynchronously."""
        if self._agents_initialized:
            return
        
        logger.info("Initializing agents with async tools")
        
        # Create all agents concurrently
        self.email_agent, self.weather_agent, self.calendar_agent, self.search_agent = await asyncio.gather(
            create_email_agent(self.model_client),
            create_weather_agent(self.model_client),
            create_calendar_agent(self.model_client),
            create_search_agent(self.model_client)
        )
        
        self.agent_list = [
            self.email_agent,
            self.weather_agent,
            self.calendar_agent,
            self.search_agent
        ]
        
        self._agents_initialized = True
        logger.info(f"Initialized {len(self.agent_list)} agents successfully")
        
        

    async def process_request(self, user_input: str) -> str:
        """Process user request with appropriate agent strategy, logging agent identities via .source if available."""
        try:
            logger.info("Starting new request")
            logger.info(f"User input: {user_input}")

            # Ensure agents are initialized
            await self._initialize_agents()
            
            # Create team with all agents
            team = MagenticOneGroupChat(
                participants=self.agent_list, 
                model_client=self.model_client,
                final_answer_prompt=self.final_answer_prompt
            )
            
            logger.info("Running multi-agent collaboration")
            
            # Run the collaboration
            chat_result = await team.run(task=user_input)
            
            # Extract the final response
            resp_messages = getattr(chat_result, "messages", None)
            if not resp_messages:
                logger.warning("No messages returned from agents")
                return "No response generated"

            logger.info("Agent Thought Process")
            for idx, msg in enumerate(resp_messages):
                # Check for .source
                if hasattr(msg, "source"):
                    agent_name = getattr(msg, "source")
                else:
                    # fallback to other attributes
                    agent_name = None
                    for attr_name in ("sender", "author", "agent", "role"):
                        if hasattr(msg, attr_name):
                            try:
                                val = getattr(msg, attr_name)
                            except Exception:
                                val = None
                            if val is not None:
                                agent_name = val
                                break
                    if agent_name is None:
                        agent_name = msg.__class__.__name__

                # Extract content
                content = None
                if hasattr(msg, "content"):
                    try:
                        content = msg.content
                    except Exception:
                        content = None
                if content is None:
                    for c_attr in ("text", "message", "body"):
                        if hasattr(msg, c_attr):
                            try:
                                content = getattr(msg, c_attr)
                            except Exception:
                                content = None
                            if content is not None:
                                break
                if content is None:
                    content = str(msg)

                logger.info(f"[Step {idx+1}] {agent_name}: {content}")

            # Final response: use last message's content
            final_msg = resp_messages[-1]
            final_content = getattr(final_msg, "content", None) or str(final_msg)
            logger.info(f"Final response: {final_content}")

            return final_content
            
        except Exception as e:
            logger.error(f"Error during request: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

    async def get_agent_status(self) -> Dict:
        """Get status of all agents and their tools."""
        await self._initialize_agents()
        
        status = {
            "initialized": self._agents_initialized,
            "total_agents": len(self.agent_list) if self.agent_list else 0,
            "agents": {}
        }
        
        if self.agent_list:
            for agent in self.agent_list:
                tool_count = len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0
                tool_names = [tool.name for tool in agent.tools] if hasattr(agent, 'tools') and agent.tools else []
                
                status["agents"][agent.name] = {
                    "description": agent.description,
                    "tool_count": tool_count,
                    "tool_names": tool_names
                }
        
        return status


# Convenience function for simple usage
async def quick_chat(user_input: str) -> str:
    """
    Simple function for direct usage without managing the orchestrator instance.
    
    Args:
        user_input: The user's request/question
        
    Returns:
        Response string or error message
    """
    assistant = PersonalAssistantOrchestrator()
    result = await assistant.process_request(user_input)
    return result


# Factory function for creating orchestrator with pre-initialized agents
async def create_orchestrator() -> PersonalAssistantOrchestrator:
    """
    Factory function to create and initialize orchestrator.
    
    Returns:
        Fully initialized PersonalAssistantOrchestrator
    """
    orchestrator = PersonalAssistantOrchestrator()
    await orchestrator._initialize_agents()
    return orchestrator


# Testing function
async def test_orchestrator():
    """Test the orchestrator functionality."""
    logger.info("Testing Orchestrator with Search Agent")
    
    try:
        # Create orchestrator
        orchestrator = await create_orchestrator()
        
        # Get status
        status = await orchestrator.get_agent_status()
        logger.info(f"Orchestrator Status:")
        logger.info(f"Initialized: {status['initialized']}")
        logger.info(f"Total Agents: {status['total_agents']}")
        
        for agent_name, agent_info in status['agents'].items():
            logger.info(f"{agent_name}: {agent_info['tool_count']} tools")
        
        # Test queries for different agents
        test_queries = [
            "What's the weather like in Mumbai?"
        ]
        
        for query in test_queries:
            logger.info(f"Testing Query: {query}")
            response = await orchestrator.process_request(query)
            logger.info(f"Response: {response[:200]}...")
        
    except Exception as e:
        logger.error(f"Orchestrator test error: {e}")


async def main():
    """Main test function."""
    logger.info("TESTING UPDATED AGENTS & ORCHESTRATOR WITH SEARCH")
    
    # Test orchestrator
    await test_orchestrator()
    
    logger.info("Test completed")


if __name__ == "__main__":
    asyncio.run(main())