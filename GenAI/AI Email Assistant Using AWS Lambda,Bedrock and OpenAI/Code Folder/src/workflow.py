import json
import logging
from datetime import datetime
from typing import Dict, List

from .utils import (
    authenticate_gmail, fetch_emails_for_date_range, fetch_emails_for_time_range, 
    determine_time_range, club_threads_together, classify_thread_with_llm, 
    apply_colored_label, draft_response_with_llm, save_gmail_draft, save_status, 
    generate_daily_summary
)
from .config import LLM_PROVIDER
from .cloud_storage import save_summary_to_s3


def process_email_workflow_by_time() -> Dict:
    """
    Time-aware workflow: Automatically determines time range and processes emails
    
    Schedule:
    - 9am: Process 5pm yesterday to 9am today  
    - 2pm: Process 9am to 2pm today
    - 5pm: Process 2pm to 5pm today
    """
    
    logging.info(f"Starting time-based email workflow using {LLM_PROVIDER.upper()}")
    
    # Initialize Gmail service
    gmail_service = authenticate_gmail()
    
    # Determine time range based on current time
    start_datetime, end_datetime = determine_time_range()
    
    # Create time-based identifier for status file
    now = datetime.now()
    time_period = f"{now.strftime('%Y-%m-%d')}_{now.hour:02d}h"
    
    # Status tracking
    status_dict = {
        'time_period': time_period,
        'start_datetime': start_datetime,
        'end_datetime': end_datetime,
        'processed_threads': {},
        'summary': {
            'total_threads': 0,
            'total_emails': 0,
            'categories': {'urgent': 0, 'important': 0, 'promotions': 0},
            'responses_drafted': 0,
            'errors': []
        }
    }
    
    try:
        # Step 1: Fetch emails for time range
        logging.info("Fetching emails for time range...")
        emails = fetch_emails_for_time_range(gmail_service, start_datetime, end_datetime)
        
        if not emails:
            logging.info("No emails to process in this time range")
            return status_dict
        
        # Continue with existing workflow...
        return process_emails_workflow_core(gmail_service, emails, status_dict)
        
    except Exception as e:
        logging.error(f"Workflow error: {e}")
        status_dict['summary']['errors'].append(str(e))
        return status_dict


def process_email_workflow(date: str) -> Dict:
    """
    Date-based workflow: Fetch emails for entire date (backward compatibility)
    """
    
    logging.info(f"Starting email workflow for {date} using {LLM_PROVIDER.upper()}")
    
    # Initialize Gmail service
    gmail_service = authenticate_gmail()
    
    # Status tracking
    status_dict = {
        'date': date,
        'processed_threads': {},
        'summary': {
            'total_threads': 0,
            'total_emails': 0,
            'categories': {'urgent': 0, 'important': 0, 'promotions': 0},
            'responses_drafted': 0,
            'errors': []
        }
    }
    
    try:
        # Step 1: Fetch all emails for the date
        logging.info("Fetching emails...")
        emails = fetch_emails_for_date_range(gmail_service, date)
        
        if not emails:
            logging.info("No emails to process")
            return status_dict
        
        return process_emails_workflow_core(gmail_service, emails, status_dict)
        
    except Exception as e:
        logging.error(f"Workflow error: {e}")
        status_dict['summary']['errors'].append(str(e))
        return status_dict


def process_emails_workflow_core(gmail_service, emails: List[Dict], status_dict: Dict) -> Dict:
    """Core email processing logic shared by both time and date workflows."""
    
    # Step 2: Club emails into threads
    logging.info("Organizing into threads...")
    threads = club_threads_together(emails)
    
    # Step 3: Process each thread
    logging.info(f"Processing {len(threads)} threads with {LLM_PROVIDER.upper()}...")
    
    for i, (thread_id, thread_data) in enumerate(threads.items(), 1):
        logging.info(f"Thread {i}/{len(threads)}: {thread_data['subject'][:60]}...")
        
        try:
            # Classify thread into one of 4 categories (including skip)
            logging.info("Classifying thread...")
            classification = classify_thread_with_llm(thread_data)
            
            category = classification['label']
            requires_response = classification['requires_response']
            
            logging.info(f"Category: {category.upper()}, Priority: {classification['priority']}, Needs response: {requires_response}")
            logging.debug(f"Reasoning: {classification['reasoning']}")
            
            # Skip emails marked as 'skip' - completely exclude from all processing
            if category == 'skip':
                logging.info("Skipping email - excluded from labeling and summary")
                continue
            
            # Execute actions
            actions_taken = []
            generated_content = {}
            
            # Apply colored label for valid categories
            if apply_colored_label(gmail_service, thread_id, category):
                actions_taken.append('applied_label')
            
            # Draft response if needed
            if requires_response and 'draft_response' in classification['tasks']:
                logging.info("Drafting response...")
                draft = draft_response_with_llm(thread_data)
                
                if save_gmail_draft(gmail_service, thread_id, draft, thread_data['subject']):
                    actions_taken.append('drafted_response')
                    generated_content['draft'] = draft
                    status_dict['summary']['responses_drafted'] += 1
            
            # Extract sender from first message  
            sender = 'Unknown'
            if thread_data['messages']:
                first_msg = thread_data['messages'][0]
                sender = first_msg.get('from', 'Unknown')
            
            # Update status
            status_dict['processed_threads'][thread_id] = {
                'subject': thread_data['subject'],
                'category': category,
                'priority': classification['priority'],
                'total_messages': thread_data['total_messages'],
                'requires_response': requires_response,
                'actions_taken': actions_taken,
                'generated_content': generated_content,
                'participants': thread_data['participants'],
                'sender': sender,  # Store extracted sender
                'content_summary': classification.get('content_summary', 'No summary available'),
                'processed_at': datetime.now().isoformat()
            }
            
            # Update summary stats
            status_dict['summary']['total_threads'] += 1
            status_dict['summary']['total_emails'] += thread_data['total_messages']
            status_dict['summary']['categories'][category] += 1
            
            logging.info(f"Thread processed successfully")
            
        except Exception as e:
            error_msg = f"Error processing thread {thread_id}: {e}"
            logging.error(f"Error: {error_msg}")
            status_dict['summary']['errors'].append(error_msg)
    
    # Generate executive summary with LLM
    logging.info("Generating executive summary...")
    executive_summary_json = generate_daily_summary(status_dict)
    status_dict['executive_summary'] = executive_summary_json
    
    # Save final status with summary locally (will be uploaded to S3 by main.py)
    logging.info("Saving status locally...")
    json_filename = save_status(status_dict.get('date', status_dict.get('time_period', 'unknown')), status_dict)
    status_dict['local_json_file'] = json_filename
    
    # Log executive summary for debugging
    logging.info("Executive summary generated successfully")
    logging.debug(f"Summary details: {json.dumps(executive_summary_json, indent=2)}")
    
    return status_dict


def analyze_results(date: str) -> None:
    """Load and display executive summary for a date."""
    try:
        filename = f"email_status_{date}.json"
        with open(filename, 'r') as f:
            status = json.load(f)
        
        # Display executive summary if available
        if 'executive_summary' in status:
            logging.info("Executive summary found")
            logging.info(status['executive_summary'])
        else:
            # Fallback to basic analysis
            summary = status['summary']
            
            logging.info(f"Email Analysis for {date}")
            logging.info(f"Total threads: {summary['total_threads']}, Total emails: {summary['total_emails']}")
            
            logging.info(f"Categories breakdown:")
            for category, count in summary['categories'].items():
                percentage = (count / summary['total_threads']) * 100 if summary['total_threads'] > 0 else 0
                logging.info(f"  {category.title()}: {count} ({percentage:.1f}%)")
            
            logging.info(f"Responses drafted: {summary['responses_drafted']}")
            
            if summary['errors']:
                logging.warning(f"Errors encountered: {len(summary['errors'])}")

    except FileNotFoundError:
        logging.error(f"No status file found for {date}")
    except Exception as e:
        logging.error(f"Error analyzing results: {e}")


def save_summary_report(date: str) -> None:
    """Save executive summary to a text file."""
    try:
        filename = f"email_status_{date}.json"
        with open(filename, 'r') as f:
            status = json.load(f)
        
        if 'executive_summary' in status:
            summary_filename = f"daily_summary_{date}.md"
            with open(summary_filename, 'w') as f:
                f.write(status['executive_summary'])
            logging.info(f"Executive summary saved to {summary_filename}")
        else:
            logging.warning("No executive summary found in status file")
            
    except Exception as e:
        logging.error(f"Error saving summary report: {e}")