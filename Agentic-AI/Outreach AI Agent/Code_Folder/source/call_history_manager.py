import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import yaml
from source.log_records import logger

# Import the CallHistory model
from db_creation import CallHistory, Base

# Load configuration
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

database_url = config["database"]["DATABASE_URL"]
engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables are created
Base.metadata.create_all(engine)

class CallHistoryManager:
    """
    Manages call history database operations
    """
    
    @staticmethod
    def create_or_update_call_history(workflow_state: Dict[str, Any]) -> Optional[str]:
        """
        Create or update call history record in database
        
        Args:
            workflow_state: Complete workflow state dictionary
            
        Returns:
            str: Campaign ID if successful, None if failed
        """
        try:
            session = SessionLocal()
            
            # Generate campaign ID if not present
            campaign_id = workflow_state.get("campaign_id")
            if not campaign_id:
                campaign_id = f"campaign_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
                workflow_state["campaign_id"] = campaign_id
            
            # Check if record already exists
            existing_record = session.query(CallHistory).filter_by(campaign_id=campaign_id).first()
            
            customer_data = workflow_state.get("customer_data", {})
            
            # Parse datetime fields safely
            def parse_datetime(dt_str):
                if dt_str:
                    try:
                        if isinstance(dt_str, str):
                            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        return dt_str
                    except:
                        return None
                return None
            
            if existing_record:
                # Update existing record
                existing_record.campaign_completed_at = parse_datetime(workflow_state.get("completed_at"))
                existing_record.campaign_status = "completed" if workflow_state.get("completed") else ("failed" if workflow_state.get("failed_at") else "in_progress")
                
                # Call details
                existing_record.call_advice = workflow_state.get("call_advice")
                existing_record.conversation_id = workflow_state.get("conversation_id")
                existing_record.call_sid = workflow_state.get("call_sid") 
                existing_record.call_status = workflow_state.get("call_status")
                existing_record.call_outcome = workflow_state.get("call_outcome")
                existing_record.call_initiated_at = parse_datetime(workflow_state.get("call_initiated_at"))
                existing_record.call_completed_at = parse_datetime(workflow_state.get("call_completed_at"))
                existing_record.transcript = workflow_state.get("transcript")
                existing_record.call_analysis = workflow_state.get("call_analysis")
                
                # Email details
                existing_record.email_sent = workflow_state.get("email_sent", False)
                existing_record.email_subject = workflow_state.get("email_subject")
                existing_record.email_content = workflow_state.get("email_content")
                existing_record.email_message_id = workflow_state.get("email_message_id")
                existing_record.email_sent_at = parse_datetime(workflow_state.get("email_sent_at"))
                existing_record.email_status = workflow_state.get("email_status")
                
                # Errors
                errors = workflow_state.get("errors", [])
                existing_record.errors = json.dumps(errors) if errors else None
                
                logger.info(f"Updated call history record: {campaign_id}")
                
            else:
                # Create new record
                call_history = CallHistory(
                    campaign_id=campaign_id,
                    customer_id=workflow_state.get("customer_id"),
                    customer_name=customer_data.get("name"),
                    customer_email=customer_data.get("email"),
                    customer_phone=customer_data.get("phone"),
                    campaign_started_at=parse_datetime(workflow_state.get("started_at")),
                    campaign_completed_at=parse_datetime(workflow_state.get("completed_at")),
                    campaign_status="completed" if workflow_state.get("completed") else ("failed" if workflow_state.get("failed_at") else "in_progress"),
                    
                    # Call details
                    call_advice=workflow_state.get("call_advice"),
                    conversation_id=workflow_state.get("conversation_id"),
                    call_sid=workflow_state.get("call_sid"),
                    call_status=workflow_state.get("call_status"),
                    call_outcome=workflow_state.get("call_outcome"),
                    call_initiated_at=parse_datetime(workflow_state.get("call_initiated_at")),
                    call_completed_at=parse_datetime(workflow_state.get("call_completed_at")),
                    transcript=workflow_state.get("transcript"),
                    call_analysis=workflow_state.get("call_analysis"),
                    
                    # Email details
                    email_sent=workflow_state.get("email_sent", False),
                    email_subject=workflow_state.get("email_subject"),
                    email_content=workflow_state.get("email_content"),
                    email_message_id=workflow_state.get("email_message_id"),
                    email_sent_at=parse_datetime(workflow_state.get("email_sent_at")),
                    email_status=workflow_state.get("email_status"),
                    
                    # Errors
                    errors=json.dumps(workflow_state.get("errors", [])) if workflow_state.get("errors") else None
                )
                
                session.add(call_history)
                logger.info(f"Created new call history record: {campaign_id}")
            
            session.commit()
            session.close()
            
            return campaign_id
            
        except Exception as e:
            logger.error(f"Error saving call history: {str(e)}")
            if session:
                session.rollback()
                session.close()
            return None
    
    @staticmethod
    def get_call_history(customer_id: str = None, campaign_id: str = None) -> list:
        """
        Retrieve call history records
        
        Args:
            customer_id: Filter by customer ID
            campaign_id: Filter by campaign ID
            
        Returns:
            list: Call history records
        """
        try:
            session = SessionLocal()
            
            query = session.query(CallHistory)
            
            if campaign_id:
                query = query.filter_by(campaign_id=campaign_id)
            elif customer_id:
                query = query.filter_by(customer_id=customer_id)
            
            records = query.all()
            session.close()
            
            return records
            
        except Exception as e:
            logger.error(f"Error retrieving call history: {str(e)}")
            return []