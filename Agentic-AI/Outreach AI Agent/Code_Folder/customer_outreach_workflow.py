from source.call_utils import make_ai_call_tool, check_call_status_tool, fetch_transcript_tool
from source.email_utils import send_email_tool
from source.customer_utils import get_customer_analytics
from source.log_records import logger
from source.workflow_state_manager import WorkflowStateManager

import json
from datetime import datetime
import yaml

from crewai import Agent, Task, Crew, Process, LLM

EMAIL_SIGNATURE = """<p>Best regards,
                <br>Alex</p>"""

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Load OpenAI API key from config
OPENAI_API_KEY = config['OpenAI']['OPENAI_API_KEY']

# Initialize LLM with OpenAI API key
llm = LLM(
    model="gpt-4o",
    temperature=0.3,
    api_key= OPENAI_API_KEY
)

insight_agent = Agent(
    role='Customer Call Strategist',
    goal='Create concise, actionable call guidance for customer success managers.',
    backstory='''You are an expert at distilling complex customer data into short, effective talking points. Your sole purpose is to provide a brief, scannable guide that a busy customer success manager can use during a live call.
    Your output must be:
    - Extremely brief: No paragraphs, only bullet points.
    - Action-oriented: Each point should be a clear instruction or talking point.
    - Personalized: Directly reference the customer's specific activity and data.
    ''',
    tools=[],
    verbose=True,
    llm=llm,
    allow_delegation=False
)

call_agent = Agent(
    role='AI Call Specialist',
    goal='Execute focused, efficient AI-guided calls avoiding unnecessary questions',
    backstory='''You are a specialist in efficient AI-powered customer communication. You make strategic calls 
    that are focused and to-the-point, avoiding lengthy conversations or unnecessary questions.''',
    tools=[make_ai_call_tool],
    verbose=True,
    llm=llm,
    allow_delegation=False
)

call_decision_agent = Agent(
    role='Call Decision Analyst',
    goal='Monitor call completion and provide email recommendations based on detailed call outcome analysis',
    backstory='''You are an expert at analyzing call outcomes and providing recommendations for follow-up emails. 
    
    Your job is to:
    1. Monitor call status and detect different outcomes (completed, failed, did not pick up)
    2. Fetch transcript when call is completed successfully
    3. Analyze the call outcome and provide specific recommendations for email content
    
    For different call scenarios, provide recommendations using context from previous agents:
    - Call completed successfully: Recommend email content referencing specific transcript points and promises made
    - Call answered but cut short/failed: Recommend email acknowledging the brief interaction and key unresolved points
    - Customer did not pick up: Recommend email with "We tried calling you regarding [specific topic]" format using insights from the first agent
    - Call initiation failed: Recommend technical follow-up or alternative contact method
    Dont give the full email just give guidance on how to generate the email as per the details.
    Always specify the call outcome clearly (completed, failed, did_not_pick, error) for the email agent.''',
    tools=[check_call_status_tool, fetch_transcript_tool],
    verbose=True,
    llm=llm,
    allow_delegation=False
)

email_agent = Agent(
    role='Email Communication Specialist',
    goal='Create and send appropriate follow-up emails based on specific call outcomes',
    backstory='''You are an expert at crafting targeted customer communications based on call outcomes:
    
    - For completed calls: Create emails referencing specific transcript points, promises made, and next steps discussed
    - For failed/interrupted calls: Create emails acknowledging the interrupted conversation and addressing unresolved topics
    - For "did not pick up" calls: Create emails using "We tried calling you regarding [specific topic]" format with relevant course information from the insight agent's analysis
    - For call errors: Create emails suggesting alternative contact methods and providing key information
    
    Always incorporate the customer's specific course interests and recent activity. Keep emails focused, helpful, and actionable.
    Use appropriate subject lines that reflect the call outcome.''',
    tools=[send_email_tool],
    verbose=True,
    llm=llm,
    allow_delegation=False
)


def create_workflow(customer_id: str, days_back: int = 30):
    """
    Create a CrewAI workflow for customer outreach with enhanced call tracking and email follow-up

    Args:
        customer_id (str): The customer ID to create the workflow for
        days_back (int): Number of days to look back for customer data

    Returns:
        Crew: The CrewAI workflow object
    
    """
    try:
        analytics_data = get_customer_analytics(
            customer_id=customer_id, 
            days_back=days_back, 
            config_path='./config.yaml'
        )
        
        if "error" in analytics_data:
            print(f"Error fetching customer data: {analytics_data['error']}")
            return None, None
        
        profile_data = analytics_data.get('profile_data', [])
        if not profile_data:
            print(f"No profile data found for customer {customer_id}")
            return None, None
        
        profile = profile_data[0]
        
        # Format customer data 
        customer_data = {
            "name": profile.get('customer_name', 'Unknown'),
            "email": profile.get('customer_email', ''),
            "phone": profile.get('phone_number', ''),
            "interactions": [],
            "last_contacted": None  
        }
        
        # Format interactions 
        engagement_data = analytics_data.get('engagement_data', [])
        for engagement in engagement_data:
            # Fix datetime handling
            analysis_period = analytics_data.get('analysis_period', {})
            end_date = analysis_period.get('end_date', '')
            if hasattr(end_date, 'strftime'):
                date_str = end_date.strftime('%Y-%m-%d')
            else:
                date_str = str(end_date)[:10] if end_date else 'Unknown'
            
            interaction = {
                "date": date_str,
                "activity": f"Watched '{engagement['course_title']}' ({engagement['course_type']}) for {engagement['total_viewtime']} minutes"
            }
            customer_data["interactions"].append(interaction)
        
        customer_data["profession"] = profile.get('profession', '')
        customer_data["field_of_interest"] = profile.get('field_of_interest', '')
        
        date_joined = profile.get('date_joined', '')
        if hasattr(date_joined, 'strftime'):
            customer_data["date_joined"] = date_joined.strftime('%Y-%m-%d')
        else:
            customer_data["date_joined"] = str(date_joined)
        
        # 
        last_active = analytics_data.get('last_active_date', '')
        if hasattr(last_active, 'strftime'):
            customer_data["last_active"] = last_active.strftime('%Y-%m-%d %H:%M:%S')
        else:
            customer_data["last_active"] = str(last_active)
        
        # Add feedback summary
        feedback_data = analytics_data.get('feedback_data', [])
        customer_data["recent_feedback"] = len(feedback_data)
        
    except Exception as e:
        logger.error(f"Error fetching customer analytics for {customer_id}: {str(e)}")
        #print(f"Error fetching customer data: {str(e)}")
        return None, None
    
    if not customer_data:
        print(f"Customer {customer_id} not found")
        return None
    
    print(f"\\n=== Starting workflow for {customer_data['name']} ===")
    
    # Initialize workflow state with enhanced call tracking
    workflow_state = {
        "customer_id": customer_id,
        "customer_data": customer_data,
        "started_at": datetime.now().isoformat(),
        "call_advice": None,
        "conversation_id": None,
        "call_sid": None,
        "call_results": None,
        "call_status": None,
        "call_outcome": None,  # completed, failed, did_not_pick, error
        "call_initiated_at": None,
        "call_completed_at": None,
        "call_analysis": None,
        "transcript": None,
        "call_metadata": None,
        "email_sent": False,
        "email_status": None,
        "email_message_id": None,
        "email_subject": None,
        "email_content": None,
        "email_sent_at": None,
        "errors": [],
        "completed": False,
        "completed_at": None,
        "failed_at": None
    }
    
    # Set shared workflow state so tools can access it
    WorkflowStateManager.set_shared_state(customer_id, workflow_state)
    
    # Define callback functions to capture task results
    def capture_call_advice(output):
        """Callback to capture call advice from insight task"""
        current_state = WorkflowStateManager.get_customer_state(customer_id)
        current_state["call_advice"] = str(output)
        WorkflowStateManager.set_shared_state(customer_id, current_state)
        logger.info(f"Captured call advice for customer {customer_id}")
        return output
    
    def capture_final_state(output):
        """Callback to capture final workflow state"""
        current_state = WorkflowStateManager.get_customer_state(customer_id)
        # Return the updated workflow state for main.py to use
        workflow_state.update(current_state)
        logger.info(f"Final workflow state captured for customer {customer_id}")
        return output
    
    insight_task = Task(
    description=f'''Analyze the following customer data and generate a call guidance script. The script should be formatted as a list of bullet points and should be no longer than 5-7 points in total.

    Customer Data:
    - Recent interactions: {customer_data["interactions"]}
    - Last contacted: {customer_data.get("last_contacted", "Never")}
    - Profession: {customer_data.get("profession", "Unknown")}
    - Field of Interest: {customer_data.get("field_of_interest", "Unknown")}
    - Last Active: {customer_data.get("last_active", "Unknown")}
    - Recent Feedback Count: {customer_data.get("recent_feedback", 0)}

    The output should be a quick-reference guide with the following sections:
    - **Goal:** A one-sentence goal for the call.
    - **Key Points:** 2-3 specific talking points based on their recent activity.
    - **Question:** 1 personalized question to ask.
    - **Next Step:** 1 clear recommendation or call to action.
    ''',
    agent=insight_agent,
    expected_output='A concise, bullet-pointed call guidance script with 4 sections: Goal, Key Points, Question, and Next Step.',
    callback=capture_call_advice
)
    
    # Prepare minimal customer data for call tool (only what's needed)
    call_customer_data = {
        "customer_id": customer_id,
        "name": customer_data.get("name"),
        "phone": customer_data.get("phone")
    }
    
    call_task = Task(
        description=f'''Execute AI call using guidance from previous task:
        
        Customer Data: {json.dumps(call_customer_data)}
        
        Make the call and return initial call status and details including conversation_id for tracking.''',
        agent=call_agent,
        expected_output='Call initiation results with conversation tracking details',
        context=[insight_task]
    )
    
    decision_task = Task(
        description='''Monitor the call from previous task and provide complete analysis:
        
        1. Check call status and wait for completion, detecting different outcomes:
           - Call completed successfully (status: done)
           - Call failed (status: failed) 
           - Customer did not pick up (status remained: initiated for too long)
           - Call initiation errors
        
        2. If call completed successfully: fetch transcript and analysis
        3. If call failed or customer didn't pick up: get appropriate details
        4. Provide specific guidance for email agent based on the actual call outcome
        
        Return complete call outcome analysis with clear recommendations for follow-up email type.''',
        agent=call_decision_agent,
        expected_output='Complete call analysis with specific outcome (completed/failed/did_not_pick/error) and email recommendations',
        context=[insight_task, call_task]
    )
    
    email_task = Task(
        description=f'''Send appropriate follow-up email based on specific call outcome:
        
        Customer: {customer_data["name"]} ({customer_data["email"]})
        
        Based on call outcome analysis from previous task:
        - If call completed: Reference transcript points, promises made, next steps
        - If call failed/interrupted: Acknowledge interrupted conversation, address unresolved topics  
        - If customer did not pick up: Use "We tried calling you regarding [specific topic]" format with relevant insights
        - If call initiation failed: Suggest alternative contact methods, provide key information
        
        Create appropriate subject line reflecting the call outcome and send personalized follow-up email.
        Use this email signature at the end {EMAIL_SIGNATURE}''',
        agent=email_agent,
        expected_output='Email sent confirmation with details about email type and content approach',
        context=[insight_task, decision_task],
        callback=capture_final_state
    )
    
    # Create Crew - same as original
    outbound_crew = Crew(
        agents=[insight_agent, call_agent, call_decision_agent, email_agent],
        tasks=[insight_task, call_task, decision_task, email_task],
        process=Process.sequential,
        verbose=True
    )
    
    return outbound_crew, workflow_state