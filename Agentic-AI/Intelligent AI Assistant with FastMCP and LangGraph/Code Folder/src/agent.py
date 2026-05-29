import os
from typing import List
from pathlib import Path
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import asyncio
from dotenv import load_dotenv
load_dotenv()
class AIAgent:
    """AI Agent with MCP integration."""
    
    def __init__(self):
        self.llm = None
        self.agent = None
        self.tools = []
        
    def initialize(self) -> bool:
        """Initialize the agent with MCP servers."""
        try:
            print("Initializing AI Agent...")
            
            # Check API keys
            if not os.getenv("OPENAI_API_KEY"):
                print("Error: OPENAI_API_KEY not found")
                return False
            
            print("API key found, initializing LLM...")
            
            # Initialize LLM
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.1
                )
                print("LLM initialized successfully")
            except Exception as e:
                print(f"LLM initialization failed: {e}")
                return False
            
            # Setup MCP servers
            print("Setting up MCP servers...")
            self._setup_mcp_servers()
            
            # Create LangGraph agent 
            print("Creating LangGraph agent...")
            try:
                if self.tools:
                    self.agent = create_react_agent(self.llm, self.tools)
                    print(f"Agent created with {len(self.tools)} tools")
                else:
                    # Create agent without tools for basic conversation
                    self.agent = create_react_agent(self.llm, [])
                    print("Agent created without tools (basic conversation mode)")
            except Exception as e:
                print(f"Agent creation failed: {e}")
                return False
                
            print("AI Agent initialization completed successfully")
            return True
            
        except Exception as e:
            print(f"Initialization failed: {e}")
            return False
    
    def _setup_mcp_servers(self):
        """Setup MCP servers with error handling."""
        print("Setting up MCP servers...")
        try:
            # Start with basic setup - test custom server first
            custom_server_params = StdioServerParameters(
                command="python",
                args=[str(Path(__file__).parent / "mcp_server.py")],
            )
            print(f"Starting custom MCP server: {custom_server_params.command} {custom_server_params.args}")
            
            async def setup_mcp_tools():
                all_tools = []
                
                # Setup custom server
                async with stdio_client(custom_server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        print("Initializing custom MCP session...")
                        await session.initialize()
                        custom_tools = await load_mcp_tools(session)
                        all_tools.extend(custom_tools)
                        print(f"Successfully loaded {len(custom_tools)} custom MCP tools")
                
                # Setup Tavily if available
                if os.getenv("TAVILY_API_KEY"):
                    print("Setting up Tavily MCP server...")
                    tavily_server_params = StdioServerParameters(
                        command="npx",
                        args=["-y", "tavily-mcp"],
                        env={
                            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
                            **os.environ
                        }
                    )
                    
                    try:
                        async with stdio_client(tavily_server_params) as (read, write):
                            async with ClientSession(read, write) as session:
                                print("Initializing Tavily MCP session...")
                                await session.initialize()
                                tavily_tools = await load_mcp_tools(session)
                                all_tools.extend(tavily_tools)
                                print(f"Successfully loaded {len(tavily_tools)} Tavily MCP tools")
                    except Exception as e:
                        print(f"Tavily setup failed: {e}")
                else:
                    print("No TAVILY_API_KEY found, skipping Tavily integration")
                
                return all_tools
            
            self.tools = asyncio.run(setup_mcp_tools())
            
            print("MCP setup completed successfully")
                
        except Exception as e:
            print(f"MCP setup failed: {e}")
         
    
    def process_command(self, command: str, conversation_history: list = None) -> str:
        """Process a command and return response."""
        async def run_with_mcp():
            try:
                # Setup MCP connections for this command 
                custom_server_params = StdioServerParameters(
                    command="python",
                    args=[str(Path(__file__).parent / "mcp_server.py")],
                )
                
                tavily_server_params = None
                if os.getenv("TAVILY_API_KEY"):
                    tavily_server_params = StdioServerParameters(
                        command="npx",
                        args=["-y", "tavily-mcp"],
                        env={
                            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
                            **os.environ
                        }
                    )
                
                # Use async with 
                if tavily_server_params:
                    async with stdio_client(custom_server_params) as (custom_read, custom_write), \
                               stdio_client(tavily_server_params) as (tavily_read, tavily_write):
                        
                        async with ClientSession(custom_read, custom_write) as custom_session, \
                                   ClientSession(tavily_read, tavily_write) as tavily_session:
                            
                            await custom_session.initialize()
                            await tavily_session.initialize()
                            
                            custom_tools = await load_mcp_tools(custom_session)
                            tavily_tools = await load_mcp_tools(tavily_session)
                            
                            all_tools = custom_tools + tavily_tools
                            agent = create_react_agent(self.llm, all_tools)
                            
                            return await self._invoke_agent(agent, command, conversation_history)
                else:
                    # Only custom tools
                    async with stdio_client(custom_server_params) as (custom_read, custom_write):
                        async with ClientSession(custom_read, custom_write) as custom_session:
                            await custom_session.initialize()
                            custom_tools = await load_mcp_tools(custom_session)
                            agent = create_react_agent(self.llm, custom_tools)
                            
                            return await self._invoke_agent(agent, command, conversation_history)
                            
            except Exception as e:
                print(f"MCP processing failed: {e}")
                return f"Error: {str(e)}"
        
        try:
            return asyncio.run(run_with_mcp())
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _invoke_agent(self, agent, command: str, conversation_history: list = None):
        """Helper method to invoke agent with proper message structure."""
        # Build message history
        messages = [
            {
                "role": "system", 
                "content": """You are an AI Research Assistant with access to web search and file management tools. Your primary role is to:

1. RESEARCH: When asked about any topic, use web search tools to gather comprehensive, current information
2. SAVE RESEARCH: After gathering information, automatically save important findings to text files using descriptive filenames (e.g., 'research_quantum_computing_2024.txt')
3. ACCESS SAVED CONTENT: Use resource tools to access and reference previously saved research
4. CONVERSATIONAL: Engage naturally while being helpful with research tasks

WORKFLOW:
- For research requests: Search → Analyze → Save → Summarize findings
- For follow-up questions: Check saved research first, then search if needed
- Always save substantial research findings for future reference
- Use clear, descriptive filenames with 'research_' prefix

Be proactive in saving valuable information and referencing previous research when relevant."""
            }
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": command})
        
        response = await agent.ainvoke({"messages": messages})
        
        # Extract response text
        if "messages" in response and response["messages"]:
            last_message = response["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return str(last_message)
        
        return str(response)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [tool.name for tool in self.tools] if self.tools else []
    
    
