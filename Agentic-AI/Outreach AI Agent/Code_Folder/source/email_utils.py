import os
import base64
import yaml

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai.tools import tool
import json
from source.log_records import logger
from source.workflow_state_manager import WorkflowStateManager

# Open and load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)


SCOPES = config['Google_API']['GOOGLE_SCOPES']
SENDER_EMAIL = config['Email']['SENDER_EMAIL']


def get_credentials(token_file: str = None,client_secrets_file: str = None) -> Credentials:
    """
    Get Google API credentials, handling OAuth flow if needed.
    
    Args:
        token_file: Path to token file (defaults to config value)
        client_secrets_file: Path to client secrets file (defaults to config value)
        
    Returns:
        Google API credentials object
    """
    try:
        if token_file is None:
            token_file =  config['Google_API']['GOOGLE_TOKEN_FILE']
        if client_secrets_file is None:
            client_secrets_file =  config['Google_API']['GOOGLE_CREDENTIALS_FILE']

        creds = None

        # Load existing credentials if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # Handle credential refresh or initial authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        raise RuntimeError("Failed to get Google API credentials") from e
        


def create_html_email(subject, sender_email, recipient_email, html_content):
    """Create HTML email message
    
    Args:
        subject (str): Email subject line
        sender_email (str): Email address to send from
        recipient_email (str): Email address to send to
        html_content (str): HTML content of the email

    Returns:
        MIMEMultipart: Email message object
    """

    try:
        if not sender_email or not recipient_email:
            logger.error("Sender and recipient email addresses must be provided")
            raise ValueError("Sender and recipient email addresses must be provided")       
        if not html_content:
            logger.error("HTML content must be provided")
            raise ValueError("HTML content must be provided")   
        if not subject:
            subject = "No Subject"    
        
        message = MIMEMultipart('alternative')
        message['to'] = recipient_email
        message['from'] = sender_email
        message['subject'] = subject

        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

        return message
    except ValueError as ve:
        logger.error(f"Error creating email: {str(ve)}")
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error creating email: {str(e)}")
        return None         
    


def send_email(service, message):
    """
    Send email using Gmail API
    
    Args:
        service: Authenticated Gmail service instance   
        message: MIMEMultipart email message to send

    Returns:
        dict: Result of email sending operation     
    
    """
    if not service or not message:
        logger.error("Service and message must be provided")    
        raise ValueError("Service and message must be provided")
    if not isinstance(message, MIMEMultipart):
        logger.error("Message must be a MIMEMultipart object")
        raise TypeError("Message must be a MIMEMultipart object")   
    if not message['to'] or not message['from']:
        logger.error("Both 'to' and 'from' fields must be set in the message")
        raise ValueError("Both 'to' and 'from' fields must be set in the message")
    if not message['subject']:
        logger.error("Subject must be set in the message")
        raise ValueError("Subject must be set in the message")
    
    try:
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        send_message = {'raw': raw_message}
        result = service.users().messages().send(userId='me', body=send_message).execute()
        return result
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return None

def send_single_email(recipient_email, sender_email, subject, html_content):
    """
    Send a single email using Gmail API
    
    Args:
        recipient_email (str): Email address to send to

        sender_email (str): Email address to send from
        subject (str): Email subject line
        html_content (str): HTML email content

    Returns:
        dict: Result of email sending operation
    """
    if not recipient_email or not sender_email:
        logger.error("Recipient and sender email addresses must be provided")
        return {'status': 'failed', 'error': 'Recipient and sender email addresses must be provided'}
    if not subject:
        subject = "No Subject"
    if not html_content:
        html_content = "<p>No content provided</p>"
    try:

        # Get credentials and create Gmail service        
        service = get_credentials()
        if not service:
            return {'status': 'failed', 'error': 'Failed to authenticate Gmail service'}

        # Create and send the email
        message = create_html_email(subject, sender_email, recipient_email, html_content)
        result = send_email(service, message)

        if result:
            return {
                'status': 'success', 
                'email': recipient_email,
                'message_id': result.get('id')
            }
        else:
            return {
                'status': 'failed', 
                'email': recipient_email,
                'error': 'Failed to send email'
            }
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return {
            'status': 'failed', 
            'email': recipient_email,
            'error': str(e)
        }
    

@tool("Send Email Tool")
def send_email_tool(recipient_email: str, subject: str, html_content: str) -> str:
    """
    Simple email sending tool that takes subject and HTML content directly
    
    Args:
        recipient_email (str): Email address to send to
        subject (str): Email subject line
        html_content (str): HTML email content
    
    Returns:
        str: JSON result of email sending
    """
    try:
        result = send_single_email(
            recipient_email=recipient_email,
            sender_email=SENDER_EMAIL,
            subject=subject,
            html_content=html_content
        )
        
        # Add subject and content to result for workflow state
        if isinstance(result, dict):
            result["subject"] = subject
            result["content"] = html_content
            
            # Update shared workflow state with email result
            shared_state = WorkflowStateManager.get_shared_state()
            for customer_id, workflow_state in shared_state.items():
                if workflow_state.get("customer_data", {}).get("email") == recipient_email:
                    workflow_state = WorkflowStateManager.update_email_sent(workflow_state, result)
                    WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                    break
            
            return json.dumps(result)
        else:
            return result
        
    except Exception as e:
        logger.error(f"Error in send_email_tool: {str(e)}")
        error_result = {
            "status": "error",
            "error": f"Error sending email: {str(e)}",
            "subject": subject,
            "content": html_content
        }
        
        # Update shared workflow state with email failure
        shared_state = WorkflowStateManager.get_shared_state()
        for customer_id, workflow_state in shared_state.items():
            if workflow_state.get("customer_data", {}).get("email") == recipient_email:
                workflow_state = WorkflowStateManager.update_email_sent(workflow_state, error_result)
                WorkflowStateManager.set_shared_state(customer_id, workflow_state)
                break
        
        return json.dumps(error_result)
