import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from email.mime.text import MIMEText
import pickle
import base64
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.utils import parsedate_to_datetime
from datetime import datetime
import pytz
from .config import *
from .prompts import get_classification_prompt_with_datetime, EMAIL_RESPONSE_PROMPT, DAILY_SUMMARY_PROMPT
from .llm_providers import call_llm


def authenticate_gmail():
    """Authenticate and return Gmail service object."""
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)


def determine_time_range() -> Tuple[str, str]:
    """Determine appropriate time range based on current IST time.
    
    Schedule (IST):
    - 9am: Fetch all emails from previous day (5pm yesterday to 9am today)
    - 2pm: Fetch emails from 9am to 2pm today
    - 5pm: Fetch emails from 2pm to 5pm today
    
    Returns:
        (start_datetime, end_datetime) in ISO format
    """
    
    # Always use IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    current_hour = now.hour
    
    if current_hour < 14:  # Before 2pm - morning run (9am)
        # Fetch from 5pm yesterday to 9am today
        yesterday_5pm = now.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
        today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
        return yesterday_5pm.isoformat(), today_9am.isoformat()
        
    elif current_hour < 17:  # 2pm-5pm - afternoon run
        # Fetch from 9am to 2pm today
        today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
        today_2pm = now.replace(hour=14, minute=0, second=0, microsecond=0)
        return today_9am.isoformat(), today_2pm.isoformat()
        
    else:  # After 5pm - evening run
        # Fetch from 2pm to 5pm today
        today_2pm = now.replace(hour=14, minute=0, second=0, microsecond=0)
        today_5pm = now.replace(hour=17, minute=0, second=0, microsecond=0)
        return today_2pm.isoformat(), today_5pm.isoformat()


def fetch_emails_for_time_range(gmail_service, start_datetime: str, end_datetime: str) -> List[Dict]:
    """Fetch emails within a specific time range using date first, then time filtering."""
    
    
    start_dt = datetime.fromisoformat(start_datetime)
    end_dt = datetime.fromisoformat(end_datetime)
    
    # Step 1: Get date range for Gmail query - exclude sent emails
    start_date = start_dt.strftime('%Y/%m/%d')
    end_date = (end_dt + timedelta(days=1)).strftime('%Y/%m/%d')  # Include end date
    
    query = f'after:{start_date} before:{end_date} -in:sent'
    
    print(f"Searching emails from {start_dt.strftime('%m/%d %I:%M%p IST')} to {end_dt.strftime('%m/%d %I:%M%p IST')}")
    print(f"Gmail date query: {query}")
    
    # Show current IST time for debugging
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    print(f"Current IST time: {current_ist.strftime('%m/%d %I:%M%p IST')}")
    
    try:
        results = gmail_service.users().messages().list(
            userId='me', q=query, maxResults=500
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print(f"No emails found in date range")
            return []
        
        # Step 2: Fetch full details and filter by exact time
        emails = []
        for message in messages:
            msg = gmail_service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()
            
            # Check if email is within time range
            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            date_header = headers.get('Date', '')
            
            if date_header:
                try:
                    email_dt = parsedate_to_datetime(date_header)
                    # Convert to IST timezone for comparison
                    ist = pytz.timezone('Asia/Kolkata')
                    email_dt_ist = email_dt.astimezone(ist)
                    
                    # start_dt and end_dt are already timezone-aware from determine_time_range()
                    # Just ensure they're in IST timezone for comparison
                    start_dt_aware = start_dt.astimezone(ist) if start_dt.tzinfo else ist.localize(start_dt)
                    end_dt_aware = end_dt.astimezone(ist) if end_dt.tzinfo else ist.localize(end_dt)
                    
                    # Only include if within exact time range
                    if start_dt_aware <= email_dt_ist <= end_dt_aware:
                        emails.append(msg)
                    else:
                        email_time_str = email_dt_ist.strftime('%m/%d %I:%M%p IST')
                        print(f"Excluding: {email_time_str} (outside current time range)")
                except Exception as e:
                    print(f"Date parsing error for {date_header}: {e}")
                    # If date parsing fails, include the email
                    emails.append(msg)
            else:
                # Include if no date header
                emails.append(msg)
        
        print(f"Fetched {len(emails)} emails after time filtering")
        return emails
        
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []


def fetch_emails_for_date_range(gmail_service, start_date: str, end_date: str = None) -> List[Dict]:
    """Fetch all emails for a given date or date range."""
    if end_date is None:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=1)
        end_date = end_dt.strftime('%Y-%m-%d')
    
    query = f'after:{start_date} before:{end_date}'
    print(f"Searching with query: {query}")
    
    try:
        results = gmail_service.users().messages().list(
            userId='me', q=query, maxResults=500
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print(f"No emails found for {start_date}")
            return []
        
        # Fetch full message details
        emails = []
        for message in messages:
            msg = gmail_service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()
            emails.append(msg)
        
        print(f"Fetched {len(emails)} emails for {start_date}")
        return emails
        
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []


def extract_message_content(payload: Dict) -> str:
    """Extract text content from Gmail message payload."""
    content = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                content += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif part['mimeType'] == 'text/html' and 'data' in part['body'] and not content:
                content += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
        content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    elif payload['mimeType'] == 'text/html' and 'data' in payload['body']:
        content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return content.strip()


def club_threads_together(emails: List[Dict]) -> Dict[str, Dict]:
    """Group emails by thread ID and create consolidated thread objects."""
    threads = {}
    
    for email in emails:
        thread_id = email['threadId']
        
        # Extract headers and content first
        headers = {h['name']: h['value'] for h in email['payload'].get('headers', [])}
        content = extract_message_content(email['payload'])
        subject = headers.get('Subject', '').strip()
        from_header = headers.get('From', '').strip()
        
        # Skip emails with no subject AND no content AND no sender
        if not subject and not content and not from_header:
            print(f"Skipping empty email thread {thread_id}")
            continue
        
        if thread_id not in threads:
            threads[thread_id] = {
                'thread_id': thread_id,
                'messages': [],
                'subject': '',
                'participants': set(),
                'total_messages': 0
            }
        
        message_data = {
            'id': email['id'],
            'date': headers.get('Date', ''),
            'from': from_header,
            'to': headers.get('To', ''),
            'subject': subject,
            'content': content
        }
        
        threads[thread_id]['messages'].append(message_data)
        threads[thread_id]['total_messages'] += 1
        
        if not threads[thread_id]['subject'] and subject:
            threads[thread_id]['subject'] = subject
        
        threads[thread_id]['participants'].add(from_header)
        threads[thread_id]['participants'].add(headers.get('To', ''))
    
    # Convert sets to lists and filter out empty threads
    valid_threads = {}
    for thread_id, thread_data in threads.items():
        thread_data['participants'] = list(filter(None, thread_data['participants']))
        
        # Only keep threads with actual content
        if thread_data['total_messages'] > 0 and (thread_data['subject'] or any(msg['content'] for msg in thread_data['messages'])):
            valid_threads[thread_id] = thread_data
    
    print(f"Organized {len(emails)} emails into {len(valid_threads)} valid threads")
    return valid_threads


def classify_thread_with_llm(thread_data: Dict) -> Dict:
    """Use llm to classify email thread into 3 categories."""
    
    # Prepare thread for LLM with full context
    messages_preview = []
    for msg in thread_data['messages'][:2]:
        messages_preview.append({
            'from': msg['from'],
            'to': msg['to'],
            'content': msg['content']
        })
    
    system_prompt = get_classification_prompt_with_datetime()
    
    user_prompt = f"""
Subject: {thread_data['subject']}
From: {thread_data['messages'][0]['from'] if thread_data['messages'] else 'Unknown'}
To: {thread_data['messages'][0]['to'] if thread_data['messages'] else 'Unknown'}
Full Thread Content: {json.dumps(messages_preview, indent=2)}
"""
    
    try:
        # Use unified LLM interface
        llm_response = call_llm(system_prompt, user_prompt, max_tokens=3000, temperature=0.1)
        
        print(f"LLM Response: {llm_response}")
        
        # Clean JSON response
        llm_response = llm_response.strip()
        if llm_response.startswith('```json'):
            llm_response = llm_response.replace('```json', '').replace('```', '')
        if llm_response.startswith('```'):
            llm_response = llm_response.replace('```', '')
        
        # Find JSON in response
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = llm_response[start_idx:end_idx+1]
        else:
            json_str = llm_response
        
        classification = json.loads(json_str)
        
        # Validate classification
        if 'category' not in classification or classification['category'] not in EMAIL_LABELS:
            classification['category'] = 'important'
        
        return {
            'label': classification['category'],
            'priority': classification.get('priority', 'medium'),
            'requires_response': classification.get('requires_response', False),
            'tasks': classification.get('tasks_to_be_done', ['apply_label']),
            'reasoning': classification.get('reasoning', 'Auto-classified'),
            'content_summary': classification.get('content_summary', 'No summary available')
        }
        
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return {
            'label': 'important',
            'priority': 'medium', 
            'requires_response': False,
            'tasks': ['apply_label'],
            'reasoning': 'Fallback due to error',
            'content_summary': 'Classification failed - manual review needed'
        }


def apply_colored_label(gmail_service, thread_id: str, label: str) -> bool:
    """Apply colored Gmail label to thread."""
    try:
        # Get all existing labels
        gmail_labels = gmail_service.users().labels().list(userId='me').execute()
        existing_labels = gmail_labels.get('labels', [])
        
        # Find exact label match (case insensitive)
        label_id = None
        for existing_label in existing_labels:
            if existing_label['name'].lower() == label.lower():
                label_id = existing_label['id']
                print(f"Found existing label: {existing_label['name']}")
                break
        
        if not label_id:
            print(f"Creating new label: {label}")
            
            # Get Gmail's predefined color for this label
            label_color = LABEL_COLORS.get(label.lower())
            
            if not label_color:
                print(f"No color defined for {label}, using default")
                label_color = {'backgroundColor': '#4a86e8', 'textColor': '#ffffff'}
            
            print(f"Using colors: bg={label_color['backgroundColor']}, text={label_color['textColor']}")
            
            # Create new colored label with exact Gmail API format
            label_body = {
                'name': label.title(),  # Title case
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show',
                'color': label_color
            }
                
            new_label = gmail_service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()
            label_id = new_label['id']
            print(f"Created label '{new_label['name']}' with ID: {label_id}")
            
            # Verify the label was created with colors
            created_label = gmail_service.users().labels().get(
                userId='me', id=label_id
            ).execute()
            if 'color' in created_label:
                print(f"Color confirmed: {created_label['color']}")
            else:
                print("Warning: No color found on created label")
        
        # Apply label to thread AND individual messages for better visibility
        print(f"Applying {label.title()} label...")
        
        # Method 1: Apply to entire thread
        gmail_service.users().threads().modify(
            userId='me',
            id=thread_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        # Method 2: Also apply to individual messages in thread for better sidebar visibility
        thread_details = gmail_service.users().threads().get(
            userId='me', id=thread_id
        ).execute()
        
        message_ids = [msg['id'] for msg in thread_details.get('messages', [])]
        
        for msg_id in message_ids:
            try:
                gmail_service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'addLabelIds': [label_id]}
                ).execute()
            except Exception as e:
                print(f"Warning: Could not apply label to message {msg_id}: {e}")
        
        print(f"Applied {label.title()} label to thread and {len(message_ids)} messages")
        
        # Verify label application
        updated_thread = gmail_service.users().threads().get(
            userId='me', id=thread_id
        ).execute()
        
        labeled_messages = 0
        for msg in updated_thread.get('messages', []):
            if label_id in msg.get('labelIds', []):
                labeled_messages += 1
        
        print(f"Label verified on {labeled_messages}/{len(message_ids)} messages")
        
        return True
        
    except Exception as e:
        print(f"Error applying label: {e}")
        return False


def draft_response_with_llm(thread_data: Dict) -> str:
    """Generate draft response using LLM."""
    last_message = thread_data['messages'][-1]
    
    system_prompt = EMAIL_RESPONSE_PROMPT
    
    user_prompt = f"""
Draft a response to:
From: {last_message['from']}
Subject: {thread_data['subject']}
Content: {last_message['content']}
"""
    
    try:
        return call_llm(system_prompt, user_prompt, max_tokens=1000, temperature=0.4)
        
    except Exception as e:
        print(f"Error generating draft: {e}")
        return "Thank you for your email. I will review and get back to you soon."


def save_gmail_draft(gmail_service, thread_id: str, draft_content: str, subject: str) -> bool:
    """Save draft in Gmail."""
    try:
        message = MIMEText(draft_content)
        message['subject'] = f"Re: {subject}"
        
        draft_body = {
            'message': {
                'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8'),
                'threadId': thread_id
            }
        }
        
        gmail_service.users().drafts().create(
            userId='me', body=draft_body
        ).execute()
        
        print(f"Saved draft for thread")
        return True
        
    except Exception as e:
        print(f"Error saving draft: {e}")
        return False


def generate_daily_summary(status_dict: Dict) -> Dict:
    """Generate executive summary JSON of daily email processing using LLM."""
    
    # Prepare detailed data for summary including actual email content
    summary_data = {
        'date': status_dict.get('date', status_dict.get('time_period', 'unknown')),
        'total_stats': status_dict['summary'],
        'urgent_threads': [],
        'important_threads': [],
        'promotions_sample': []
    }
    
    # Collect ONLY urgent and important threads with full context
    # Promotions are excluded from detailed processing to reduce LLM token usage
    for thread_id, thread in status_dict['processed_threads'].items():
        # Skip promotions - only include count in summary
        if thread['category'] == 'promotions':
            continue
            
        # Use the sender already extracted and stored in workflow
        sender = thread.get('sender', 'Unknown')
        
        thread_summary = {
            'subject': thread['subject'] if thread['subject'].strip() else f"Email from {sender}",
            'category': thread['category'],
            'requires_response': thread.get('requires_response', False),
            'sender': sender,
            'content_summary': thread.get('content_summary', 'No summary available'),
            'generated_content': thread.get('generated_content', {}),
            'priority': thread.get('priority', 'medium')
        }
        
        if thread['category'] == 'urgent':
            summary_data['urgent_threads'].append(thread_summary)
        elif thread['category'] == 'important':
            summary_data['important_threads'].append(thread_summary)
    
    # Sort by response requirement
    summary_data['urgent_threads'].sort(key=lambda x: x['requires_response'], reverse=True)
    summary_data['important_threads'].sort(key=lambda x: x['requires_response'], reverse=True)
    
    system_prompt = DAILY_SUMMARY_PROMPT
    
    user_prompt = f"Generate executive summary JSON for this email processing data:\n{json.dumps(summary_data, indent=2)}"
    
    try:
        llm_response = call_llm(system_prompt, user_prompt, max_tokens=3000, temperature=0.2)
        
        # Clean and parse JSON response
        llm_response = llm_response.strip()
        if llm_response.startswith('```json'):
            llm_response = llm_response.replace('```json', '').replace('```', '')
        if llm_response.startswith('```'):
            llm_response = llm_response.replace('```', '')
        
        # Find JSON in response
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = llm_response[start_idx:end_idx+1]
        else:
            json_str = llm_response
        
        summary_json = json.loads(json_str)
        return summary_json
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {
            "date": status_dict.get('date', status_dict.get('time_period', 'unknown')),
            "overview": {
                "total_emails": status_dict['summary']['total_emails'],
                "key_themes": "Summary generation failed"
            },
            "urgent_items": [],
            "important_items": []
        }


def save_status(date: str, status_dict: Dict) -> str:
    """Save processing status to JSON file and return filename."""
    try:
        filename = f"email_status_{date}.json"
        with open(filename, 'w') as f:
            json.dump(status_dict, f, indent=2, default=str)
        logging.info(f"Status saved to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error saving status: {e}")
        return ""