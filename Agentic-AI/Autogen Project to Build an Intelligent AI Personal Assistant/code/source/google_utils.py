import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from source.configurations import config
SCOPES = config.GOOGLE_SCOPES

def get_credentials(token_file: str = None,client_secrets_file: str = None) -> Credentials:
    """
    Get Google API credentials, handling OAuth flow if needed.
    
    Args:
        token_file: Path to token file (defaults to config value)
        client_secrets_file: Path to client secrets file (defaults to config value)
        
    Returns:
        Google API credentials object
    """
    if token_file is None:
        token_file = config.GOOGLE_TOKEN_FILE
    if client_secrets_file is None:
        client_secrets_file = config.GOOGLE_CREDENTIALS_FILE
    
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

    return creds


def get_gmail_service():
    """
    Get Gmail service credentials.
    
    Returns:
        Google API credentials for Gmail
    """
    return get_credentials()


def get_calendar_service():
    """
    Get Google Calendar service instance.
    
    Returns:
        Google Calendar API service object
    """
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)
