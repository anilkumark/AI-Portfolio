
import streamlit as st
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import traceback
from agent import AIAgent


def initialize_agent():
    """Initialize the AI agent."""
    if 'agent' not in st.session_state:
        with st.spinner('Initializing AI Assistant...'):
            try:
                agent = AIAgent()
                success = agent.initialize()
                
                if success:
                    st.session_state.agent = agent
                    st.success('AI Assistant ready')
                    return True
                else:
                    st.error('Failed to initialize agent')
                    return False
            except Exception as e:
                st.error(f'Initialization error: {e}')
                st.code(traceback.format_exc())
                return False
    return True


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="AI Research Assistant",
        page_icon="🔬",
        layout="centered"
    )
    
    st.title("🔬 AI Research Assistant")
    st.caption("Advanced AI agent that researches topics, searches the web, and saves findings to documents for future reference.")
    
    # Check API keys
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY environment variable")
        st.code("export OPENAI_API_KEY='your-key'")
        st.stop()
    
    # Initialize agent
    if not initialize_agent():
        st.stop()
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner('Processing...'):
                try:
                    # Pass conversation history for context
                    response = st.session_state.agent.process_command(
                        prompt, 
                        conversation_history=st.session_state.messages
                    )
                    st.markdown(response)
                except Exception as e:
                    response = f"Error: {str(e)}"
                    st.markdown(response)
        
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()