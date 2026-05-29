import json
from datetime import datetime
from typing import Dict, Any
from source.log_records import logger

class WorkflowStateManager:
    """
    Manages workflow state updates throughout the customer outreach process
    """
    
    @staticmethod
    def update_call_initiated(workflow_state: Dict[str, Any], call_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow state when call is initiated"""
        try:
            workflow_state.update({
                "conversation_id": call_result.get("conversation_id"),
                "call_sid": call_result.get("call_sid"), 
                "call_status": call_result.get("status"),
                "call_initiated_at": call_result.get("initiated_at"),
                "call_phone": call_result.get("phone")
            })
            logger.info(f"Updated workflow state with call initiation: {call_result.get('conversation_id')}")
        except Exception as e:
            logger.error(f"Error updating call initiated state: {str(e)}")
            workflow_state["errors"].append(f"Error updating call initiated: {str(e)}")
        
        return workflow_state
    
    @staticmethod
    def update_call_status(workflow_state: Dict[str, Any], status_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow state with call status and outcome"""
        try:
            workflow_state.update({
                "call_status": status_result.get("call_status"),
                "call_outcome": status_result.get("call_outcome"),
                "call_completed_at": datetime.now().isoformat() if status_result.get("call_outcome") in ["completed", "failed", "did_not_pick"] else None
            })
            logger.info(f"Updated workflow state with call status: {status_result.get('call_outcome')}")
        except Exception as e:
            logger.error(f"Error updating call status: {str(e)}")
            workflow_state["errors"].append(f"Error updating call status: {str(e)}")
        
        return workflow_state
    
    @staticmethod  
    def update_transcript(workflow_state: Dict[str, Any], transcript_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow state with call transcript"""
        try:
            workflow_state.update({
                "transcript": transcript_result.get("transcript"),
                "call_analysis": transcript_result.get("analysis"),
                "call_metadata": transcript_result.get("metadata")
            })
            logger.info(f"Updated workflow state with transcript for: {workflow_state.get('conversation_id')}")
        except Exception as e:
            logger.error(f"Error updating transcript: {str(e)}")
            workflow_state["errors"].append(f"Error updating transcript: {str(e)}")
        
        return workflow_state
    
    @staticmethod
    def update_email_sent(workflow_state: Dict[str, Any], email_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow state when email is sent"""
        try:
            workflow_state.update({
                "email_sent": True,
                "email_status": email_result.get("status"),
                "email_message_id": email_result.get("message_id"),
                "email_subject": email_result.get("subject"),
                "email_content": email_result.get("content"),
                "email_sent_at": datetime.now().isoformat()
            })
            logger.info(f"Updated workflow state with email sent: {email_result.get('status')}")
        except Exception as e:
            logger.error(f"Error updating email sent: {str(e)}")
            workflow_state["errors"].append(f"Error updating email sent: {str(e)}")
        
        return workflow_state

    @staticmethod
    def get_shared_state():
        """Get shared workflow state - simple in-memory storage for now"""
        if not hasattr(WorkflowStateManager, '_shared_state'):
            WorkflowStateManager._shared_state = {}
        return WorkflowStateManager._shared_state
    
    @staticmethod
    def set_shared_state(customer_id: str, workflow_state: Dict[str, Any]):
        """Set shared workflow state"""
        shared_state = WorkflowStateManager.get_shared_state()
        shared_state[customer_id] = workflow_state
        logger.info(f"Set shared workflow state for customer: {customer_id}")
    
    @staticmethod
    def get_customer_state(customer_id: str) -> Dict[str, Any]:
        """Get workflow state for specific customer"""
        shared_state = WorkflowStateManager.get_shared_state()
        return shared_state.get(customer_id, {})