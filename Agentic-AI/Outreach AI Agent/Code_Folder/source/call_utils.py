
import json
from datetime import datetime
import time

# ElevenLabs for AI calling
from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import ConversationInitiationData
import yaml
from crewai.tools import tool
from source.log_records import logger
from source.workflow_state_manager import WorkflowStateManager
# Environment variables
# Open and load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

ELEVENLABS_API_KEY = config['ElevenLabs']['ELEVENLABS_API_KEY']
ELEVENLABS_AGENT_ID = config['ElevenLabs']['ELEVENLABS_AGENT_ID']
PHONE_NUMBER_ID = config['ElevenLabs']['PHONE_NUMBER_ID']   
SENDER_EMAIL = config['Email']['SENDER_EMAIL']

@tool("Make AI Call")
def make_ai_call_tool(customer_data: dict, call_guidance: dict) -> str:
    """
    Make an AI-guided call using ElevenLabs and return call details.
    
    Args:
        customer_data: Dictionary containing customer information (name, phone)
        call_guidance: Dictionary containing call guidance instructions

    Returns:
        JSON string with call details or error message
    """
    # Validate inputs
    if not isinstance(customer_data, dict):
        logger.error("Customer data must be a dictionary")
        raise ValueError("customer_data must be a dictionary")
    if not isinstance(call_guidance, dict):
        logger.error("Call guidance must be a dictionary")
        raise ValueError("call_guidance must be a dictionary")
    
    # Ensure name and phone are non-empty strings
    name = customer_data.get("name", "").strip()
    phone = customer_data.get("phone", "").strip()
    
    if not name or not phone:
        logger.error("Customer name and phone must be non-empty strings")
        raise ValueError("customer name or phone must be a non-empty string")
    
    # Ensure phone number has country code (e.g., +1 for US)
    if not phone.startswith("+"):
        # Default to US/IN country code if not present; adjust as needed
        phone = "+91" + phone.lstrip("0") #IN country code
        
        # Uncomment the line above if you want to use US country code instead of IN
        #phone = "+1" + phone.lstrip("0")

    try:

        dynamic_vars = {
            "customer_name": name,
            "call_guidance": str(call_guidance)
        }
        
        call_config = ConversationInitiationData(dynamic_variables=dynamic_vars)
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        print(f"Making call to {name} at {phone}...")
        
        # Record call initiation time for tracking
        call_initiated_at = datetime.now().isoformat()
        
        response = client.conversational_ai.twilio.outbound_call(
            agent_id=ELEVENLABS_AGENT_ID,
            agent_phone_number_id=PHONE_NUMBER_ID,
            to_number=phone,
            conversation_initiation_client_data=call_config
        )
        # Check if the call was successfully initiated
        if response.success:
            call_result = {
                "status": "call_initiated",
                "customer": name,
                "phone": phone,
                "conversation_id": response.conversation_id,
                "call_sid": response.call_sid,
                "message": response.message,
                "initiated_at": call_initiated_at
            }
            
            # Update shared workflow state
            customer_id = customer_data.get("customer_id", name)
            workflow_state = WorkflowStateManager.get_customer_state(customer_id)
            if workflow_state:
                workflow_state = WorkflowStateManager.update_call_initiated(workflow_state, call_result)
                WorkflowStateManager.set_shared_state(customer_id, workflow_state)
            
            return json.dumps(call_result)
        else:
            call_result = {
                "status": "failed",
                "error": "Call initiation failed",
                "customer": name,
                "initiated_at": call_initiated_at
            }
            
            # Update shared workflow state with failure
            customer_id = customer_data.get("customer_id", name)  
            workflow_state = WorkflowStateManager.get_customer_state(customer_id)
            if workflow_state:
                workflow_state["errors"].append("Call initiation failed")
                WorkflowStateManager.set_shared_state(customer_id, workflow_state)
            
            return json.dumps(call_result)
    except Exception as e:
        logger.error(f"Error making call to {name} at {phone}: {str(e)}")
        # Return error details in JSON format
        return json.dumps({
            "status": "error",
            "customer": name,
            "phone": phone,
            "error": f"Error making call: {str(e)}"
        }) 



@tool("Check AI Call Status")
def check_call_status_tool(conversation_id: str) -> str:
    """    
    
    Check the status of an AI call and return its outcome.

    Args:
        conversation_id: The ID of the conversation to check status for

    Returns:
        JSON string with call status and outcome

    """
    # Constants for call status checking
    max_wait_time = 300  # 5 minutes max
    check_interval = 10  # Check every 10 seconds
    no_pickup_threshold = 60  # 1 minute before considering "did not pick up
    elapsed = 0  # Time elapsed since call initiation
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    no_pickup_detected = False
    while elapsed < max_wait_time:
        try:
            conv = client.conversational_ai.conversations.get(conversation_id=conversation_id)
            status = conv.status
            
            print(f"Call status: {status} (waited {elapsed}s)")
            
            if status == "done":
                status_result = {
                    "status": "ready_for_transcript",
                    "conversation_id": conversation_id,
                    "call_status": status,
                    "call_outcome": "completed"
                }
                
                # Update shared workflow state
                shared_state = WorkflowStateManager.get_shared_state()
                for customer_id, workflow_state in shared_state.items():
                    if workflow_state.get("conversation_id") == conversation_id:
                        workflow_state = WorkflowStateManager.update_call_status(workflow_state, status_result)
                        WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                        break
                
                return json.dumps(status_result)
            elif status == "failed":
                error_info = getattr(conv.metadata, 'error', 'Call failed') if hasattr(conv, 'metadata') else 'Call failed'
                status_result = {
                    "status": "call_failed",
                    "conversation_id": conversation_id,
                    "call_status": status,
                    "call_outcome": "failed",
                    "error": error_info
                }
                
                # Update shared workflow state
                shared_state = WorkflowStateManager.get_shared_state()
                for customer_id, workflow_state in shared_state.items():
                    if workflow_state.get("conversation_id") == conversation_id:
                        workflow_state = WorkflowStateManager.update_call_status(workflow_state, status_result)
                        WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                        break
                
                return json.dumps(status_result)
            elif status == "initiated":
                # Check if call has been in "initiated" state too long (likely no pickup)
                if elapsed >= no_pickup_threshold and not no_pickup_detected:
                    no_pickup_detected = True
                    print(f"Call likely not picked up - been 'initiated' for {elapsed}s")
                
                # If we've waited long enough and still initiated, treat as no pickup
                if elapsed >= (no_pickup_threshold * 1):
                    status_result = {
                        "status": "did_not_pick",
                        "conversation_id": conversation_id,
                        "call_status": status,
                        "call_outcome": "did_not_pick",
                        "message": f"Customer did not pick up call after {elapsed}s (status remained 'initiated')"
                    }
                    
                    # Update shared workflow state
                    shared_state = WorkflowStateManager.get_shared_state()
                    for customer_id, workflow_state in shared_state.items():
                        if workflow_state.get("conversation_id") == conversation_id:
                            workflow_state = WorkflowStateManager.update_call_status(workflow_state, status_result)
                            WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                            break
                    
                    return json.dumps(status_result)
                    
                time.sleep(check_interval)
                elapsed += check_interval
                continue
                
            elif status in ["in-progress", "processing"]:
                # Reset no pickup detection if call progresses
                no_pickup_detected = False
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            else:
                return json.dumps({
                    "status": "unknown_status",
                    "call_status": status,
                    "conversation_id": conversation_id,
                    "call_outcome": "unknown"
                })
                
        except Exception as e:
            logger.error(f"Error checking call status for {conversation_id}: {str(e)}")
            # Return error details in JSON format
            return json.dumps({
                "status": "error",
                "error": f"Error checking status: {str(e)}"
            })
    
    # Timeout case - determine outcome based on final status
    final_status = "unknown"
    try:
        conv = client.conversational_ai.conversations.get(conversation_id=conversation_id)
        final_status = conv.status
    except:
        pass
    
    if final_status == "initiated":
        return json.dumps({
            "status": "did_not_pick",
            "call_outcome": "did_not_pick", 
            "error": f"Timeout after {max_wait_time}s - call remained in 'initiated' state (customer likely did not pick up)"
        })
    else:
        return json.dumps({
            "status": "timeout",
            "call_outcome": "timeout",
            "error": f"Timeout after {max_wait_time}s waiting for call completion, final status: {final_status}"
        })


@tool("Fetch Call Transcript")
def fetch_transcript_tool(conversation_id: str) -> str:
    """
    Fetch conversation transcript - only call when status is done
    
    Args:
        conversation_id: The ID of the conversation to fetch transcript for

    Returns:
        JSON string with transcript details or error message    

    """
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    try:
        time.sleep(10)
        conv = client.conversational_ai.conversations.get(conversation_id=conversation_id)

        if conv.status == "done":
        
            # Convert the transcript to a readable string format
            transcript_lines = []
            if hasattr(conv, 'transcript') and isinstance(conv.transcript, list):
                for turn in conv.transcript:
                    # Skip if no message or message is empty
                    if getattr(turn, 'message', None):
                        # Safe strip
                        role = getattr(turn, 'role', 'unknown')
                        message = turn.message.strip()
                        transcript_lines.append(f"{role}: {message}")
            # Combine lines into a single string
            transcript_str = "\n".join(transcript_lines)

            transcript_result = {
                "status": "success",
                "conversation_id": conversation_id,
                "transcript": transcript_str,
                "analysis": str(conv.analysis) if conv.analysis else "",
                "metadata": conv.metadata if isinstance(conv.metadata, dict) else str(conv.metadata or "")
            }
            
            # Update shared workflow state with transcript
            shared_state = WorkflowStateManager.get_shared_state()
            for customer_id, workflow_state in shared_state.items():
                if workflow_state.get("conversation_id") == conversation_id:
                    workflow_state = WorkflowStateManager.update_transcript(workflow_state, transcript_result)
                    WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                    break

            return json.dumps(transcript_result)

        else:
            return json.dumps({
                "status": "not_ready",
                "call_status": conv.status,
                "error": f"Transcript not ready, call status: {conv.status}"
            })

    except Exception as e:
        logger.error(f"Error fetching transcript for {conversation_id}: {str(e)}")
        # Return error details in JSON format
        return json.dumps({
            "status": "error",
            "error": f"Error fetching transcript: {str(e)}"
        })
