import json
import requests
import os
import sys
import logging
from datetime import datetime, timedelta
import subprocess
# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import config to set environment variables
from src import config
from src.workflow import process_email_workflow_by_time
from src.cloud_storage import (
    setup_logging, cleanup_and_notify_success, 
    handle_error_and_notify
)


def send_slack_notification(webhook_url: str, date: str, summary_data: dict) -> bool:
    """Send formatted email summary to Slack."""
    
    # Get the JSON executive summary
    exec_summary = summary_data.get('executive_summary', {})
    
    if not exec_summary or 'overview' not in exec_summary:
        # Fallback to basic stats
        total_threads = summary_data['summary']['total_threads']
        categories = summary_data['summary']['categories']
        responses_drafted = summary_data['summary']['responses_drafted']
        
        basic_message = f"*Daily Email Summary - {date}*\n\n*Overview:* {total_threads} emails processed | {responses_drafted} responses drafted"
        
        message = {
            "text": f"📧 Daily Email Summary - {date}",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": basic_message}}]
        }
    else:
        # Format JSON summary into proper Slack markdown
        overview = exec_summary['overview']
        urgent_items = exec_summary.get('urgent_items', [])
        important_items = exec_summary.get('important_items', [])
        insights = exec_summary.get('insights', {})
        
        # Build formatted message
        formatted_text = f"*Daily Email Summary - {date}*\n\n"
        
        # Overview section
        formatted_text += f"*Overview*\n"
        formatted_text += f"• {overview['total_emails']} emails processed ({overview['urgent_count']} urgent, {overview['important_count']} important, {overview['promotions_count']} promotions)\n"
        formatted_text += f"• {overview['responses_drafted']} responses drafted automatically\n"
        formatted_text += f"• {overview.get('key_themes', 'Various topics')}\n\n"
        
        # Urgent section
        if urgent_items:
            formatted_text += "*🔴 Urgent - Immediate Action Required*\n"
            for item in urgent_items[:10]:
                deadline_text = f" (Deadline: {item['deadline']})" if item.get('deadline') else ""
                formatted_text += f"• *{item['sender']}:* {item['context']} - {item['action']}{deadline_text}\n"
            formatted_text += "\n"
        else:
            formatted_text += "*🔴 Urgent - Immediate Action Required*\nNo urgent items\n\n"
        
        # Important section  
        if important_items:
            formatted_text += "*🟠 Important - Attention Needed*\n"
            for item in important_items[:10]:
                formatted_text += f"• *{item['sender']}:* {item['context']} - {item['action']}\n"
            formatted_text += "\n"
        else:
            formatted_text += "*🟠 Important - Attention Needed*\nNo important items\n\n"
        
        # Quick stats
        formatted_text += "*📊 Quick Stats*\n"
        formatted_text += f"• Promotions: {overview['promotions_count']} (auto-processed)\n"
        formatted_text += f"• Responses drafted: {overview['responses_drafted']}\n"
        if insights.get('response_rate'):
            formatted_text += f"• Response rate: {insights['response_rate']}\n"
        formatted_text += "\n"
        
        # Next actions
        formatted_text += "*✅ Next Actions*\n"
        formatted_text += f"• Review {overview['urgent_count']} urgent items above\n"
        formatted_text += f"• Respond to {overview['important_count']} important emails\n"
        formatted_text += "• Check drafts folder for prepared responses"
        
        message = {
            "text": f"📧 Daily Email Summary - {date}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": formatted_text
                    }
                }
            ]
        }
    
    # Add action buttons
    message["blocks"].append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📧 Check Gmail"
                },
                "url": "https://mail.google.com",
                "action_id": "check_gmail"
            },
            {
                "type": "button", 
                "text": {
                    "type": "plain_text",
                    "text": "📝 Drafts"
                },
                "url": "https://mail.google.com/#drafts",
                "action_id": "check_drafts"
            }
        ]
    })
    
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        
        if response.status_code == 200:
            logging.info("Slack notification sent successfully")
            return True
        else:
            logging.error(f"Slack notification failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Error sending to Slack: {e}")
        return False


def main():
    """Main function for cron job or manual execution."""
    
    # Setup logging first
    current_time = datetime.now()
    time_period = f"{current_time.strftime('%Y-%m-%d')}_{current_time.hour:02d}h"
    log_filename = setup_logging(time_period)
    
    logging.info("Starting Gmail organizer with cloud storage integration")
    
    # Get webhook URL from environment
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        logging.error("SLACK_WEBHOOK_URL environment variable not set")
        handle_error_and_notify(Exception("SLACK_WEBHOOK_URL not configured"), time_period, log_filename)
        return
    
    # Use time-based workflow (automatically determines time range)
    logging.info("Processing emails using time-based workflow and sending to Slack...")
    
    try:
        # Run time-based email workflow
        results = process_email_workflow_by_time()
        
        # Create readable time range for Slack notification
        start_dt = results.get('start_datetime', '')
        end_dt = results.get('end_datetime', '')
        
        if start_dt and end_dt:
            start = datetime.fromisoformat(start_dt)
            end = datetime.fromisoformat(end_dt)
            
            # Format: "Sep 1 5pm to Sep 2 9am"
            readable_range = f"{start.strftime('%b %d %I%p').replace(' 0', ' ')} to {end.strftime('%b %d %I%p').replace(' 0', ' ')}"
        else:
            readable_range = results.get('time_period', datetime.now().strftime('%Y-%m-%d_%Hh'))
        
        # Send to Slack
        slack_success = send_slack_notification(webhook_url, readable_range, results)
        
        if slack_success:
            logging.info(f"Email summary completed for {readable_range}")
            
            # Handle successful completion: save to S3, send notifications, cleanup logs
            cleanup_success = cleanup_and_notify_success(results, time_period, log_filename)
            
            if cleanup_success:
                logging.info("All data successfully saved to S3 and notifications sent")
                
                # Shutdown EC2 after successful processing
                try:
                    logging.info("Shutting down EC2 instance safely...")
                    # subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
                except Exception as shutdown_error:
                    logging.info(f"EC2 shutdown failed (this is normal if not running on EC2): {shutdown_error}")
            else:
                logging.error("Failed to save data to S3 or send notifications")
                handle_error_and_notify(Exception("Cloud storage cleanup failed"), time_period, log_filename)
                
        else:
            logging.error(f"Failed to send summary for {readable_range}")
            handle_error_and_notify(Exception("Slack notification failed"), time_period, log_filename)
            
    except Exception as e:
        logging.error(f"Error in daily summary: {e}")
        
        # Handle error: send SNS notifications and cleanup logs
        handle_error_and_notify(e, time_period, log_filename)
        
        # Also send error notification to Slack as backup
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        error_message = {
            "text": f"Email Summary Failed - {current_time}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Email processing failed at {current_time}*\n\nError: `{str(e)}`"
                    }
                }
            ]
        }
        
        try:
            requests.post(webhook_url, json=error_message, timeout=10)
        except:
            logging.error("Failed to send error notification to Slack")
        
        # Shutdown even on error to avoid costs
        try:
            logging.info("Shutting down EC2 instance after error...")
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except Exception as shutdown_error:
            logging.info(f"EC2 shutdown failed (this is normal if not running on EC2): {shutdown_error}")
            handle_error_and_notify(shutdown_error, time_period, log_filename)


if __name__ == "__main__":
    main()