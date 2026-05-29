from customer_outreach_workflow import create_workflow
from datetime import datetime
from source.call_history_manager import CallHistoryManager
from source.log_records import logger



def run_campaign(customer_id: str, days_back: int = 30):
    """
    run the outbound campaign for a specific customer 

    Args:
        customer_id (str): The customer ID to run the campaign for
        days_back (int): Number of days to look back for customer data
    
    Returns:
        dict: Final workflow state with campaign results and tracking information
    
    
    """
    print(f"Starting outbound campaign for customer: {customer_id}")
    
    crew, workflow_state = create_workflow(customer_id, days_back)
    if not crew:
        return None
    
    # Save initial campaign state to database 
    campaign_id = CallHistoryManager.create_or_update_call_history(workflow_state)
    if campaign_id:
        workflow_state["campaign_id"] = campaign_id
        logger.info(f"Initial campaign state saved with ID: {campaign_id}")
    
    try:
        result = crew.kickoff()
        
        # Store final state with enhanced tracking
        workflow_state["campaign_result"] = str(result)
        workflow_state["completed"] = True
        workflow_state["completed_at"] = datetime.now().isoformat()
        
        # Save call history to database
        campaign_id = CallHistoryManager.create_or_update_call_history(workflow_state)
        if campaign_id:
            workflow_state["campaign_id"] = campaign_id
            logger.info(f"Campaign data saved to database with ID: {campaign_id}")
        else:
            logger.error(f"Failed to save campaign data to database for customer: {customer_id}")
        
        print(f"Campaign completed for {customer_id}")
        return workflow_state
        
    except Exception as e:
        error_msg = str(e)
        workflow_state["errors"].append(error_msg)
        workflow_state["completed"] = False
        workflow_state["failed_at"] = datetime.now().isoformat()
        
        # Save failed campaign to database
        campaign_id = CallHistoryManager.create_or_update_call_history(workflow_state)
        if campaign_id:
            workflow_state["campaign_id"] = campaign_id
            logger.info(f"Failed campaign data saved to database with ID: {campaign_id}")
        
        print(f"Error running campaign for {customer_id}: {error_msg}")
        logger.error(f"Campaign failed for {customer_id}: {error_msg}")
        return workflow_state
    

if __name__ == "__main__":
    target_customer_id = "126" # Replace with actual customer ID

    # Run the complete campaign 
    campaign_result = run_campaign(target_customer_id, days_back=30)

    if campaign_result:
        print("\nCampaign Summary:")
        print(f"Customer ID: {campaign_result['customer_id']}")
        print(f"Started: {campaign_result['started_at']}")
        print(f"Completed: {campaign_result.get('completed', False)}")

        if campaign_result.get('errors'):
            print(f"Errors: {campaign_result['errors']}")

        if campaign_result.get('completed'):
            print("Campaign completed successfully!")
    else:
        print("\nCampaign failed to start")    