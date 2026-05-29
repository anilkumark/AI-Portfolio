
import boto3
import glob
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from .config import AWS_REGION, S3_BUCKET, S3_LOGS_PREFIX, S3_SUMMARIES_PREFIX, SNS_TOPIC_ARN


def get_aws_clients():
    """Get AWS clients for S3 and SNS."""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        sns_client = boto3.client('sns', region_name=AWS_REGION)
        return s3_client, sns_client
    except Exception as e:
        logging.error(f"Failed to create AWS clients: {e}")
        raise


def save_summary_to_s3(summary_data: Dict, time_period: str) -> bool:
    """Save email summary JSON to S3 bucket."""
    try:
        s3_client, _ = get_aws_clients()
        
        # Create S3 key with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        s3_key = f"{S3_SUMMARIES_PREFIX}email_summary_{time_period}_{timestamp}.json"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(summary_data, indent=2, default=str),
            ContentType='application/json'
        )
        
        logging.info(f"Successfully saved summary to S3: s3://{S3_BUCKET}/{s3_key}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to save summary to S3: {e}")
        return False


def save_logs_to_s3(log_filename: str) -> bool:
    """Save log file to S3 and delete local copy."""
    try:
        if not os.path.exists(log_filename):
            logging.warning(f"Log file {log_filename} not found")
            return False
            
        s3_client, _ = get_aws_clients()
        
        # Create S3 key for log file
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        s3_key = f"{S3_LOGS_PREFIX}gmail_organizer_{timestamp}.log"
        
        # Upload log file to S3
        with open(log_filename, 'rb') as log_file:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=log_file,
                ContentType='text/plain'
            )
        
        logging.info(f"Successfully saved logs to S3: s3://{S3_BUCKET}/{s3_key}")
        
        # Delete local log file after successful upload
        os.remove(log_filename)
        logging.info(f"Deleted local log file: {log_filename}")
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to save logs to S3: {e}")
        return False


def send_sns_notification(subject: str, message: str, success: bool = True) -> bool:
    """Send SNS notification about processing status."""
    try:
        _, sns_client = get_aws_clients()
        
        # Add status indicator to subject
        status_prefix = "[SUCCESS]" if success else "[ERROR]"
        full_subject = f"{status_prefix} Gmail Organizer - {subject}"
        
        # Add timestamp to message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')
        full_message = f"Timestamp: {timestamp}\n\n{message}"
        
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=full_message,
            Subject=full_subject
        )
        
        logging.info(f"SNS notification sent successfully: {response['MessageId']}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send SNS notification: {e}")
        return False


def setup_logging(time_period: str) -> str:
    """Setup logging configuration and return log filename."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"logs/gmail_organizer_{time_period}_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logging.info(f"Logging initialized for time period: {time_period}")
    return log_filename


def cleanup_local_json_files(time_period: str) -> bool:
    """Clean up local JSON status files after successful S3 upload."""
    try:
        # Common patterns for JSON files that might be created
        import glob
        patterns = [
            f"email_status_{time_period}.json",
            f"email_status_{time_period.split('_')[0]}.json",  # date only
            "email_status_*.json"  # any status files from today
        ]
        
        files_deleted = 0
        for pattern in patterns:
            matching_files = glob.glob(pattern)
            for file_path in matching_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Deleted local JSON file: {file_path}")
                    files_deleted += 1
        
        logging.info(f"Cleaned up {files_deleted} local JSON files")
        return True
        
    except Exception as e:
        logging.error(f"Error cleaning up local JSON files: {e}")
        return False


def cleanup_and_notify_success(summary_data: Dict, time_period: str, log_filename: str) -> bool:
    """Handle successful completion: save to S3, send notifications, cleanup logs and JSON files."""
    try:
        # Save summary to S3
        s3_success = save_summary_to_s3(summary_data, time_period)
        if not s3_success:
            raise Exception("Failed to save summary to S3")
        
        # Send success notification
        processed_count = summary_data.get('summary', {}).get('total_threads', 0)
        urgent_count = summary_data.get('summary', {}).get('categories', {}).get('urgent', 0)
        important_count = summary_data.get('summary', {}).get('categories', {}).get('important', 0)
        
        success_message = f"""Gmail processing completed successfully!
        
Time Period: {time_period}
Total Emails Processed: {processed_count}
Urgent Items: {urgent_count}
Important Items: {important_count}
        
Summary saved to S3: s3://{S3_BUCKET}/{S3_SUMMARIES_PREFIX}
Slack notification sent successfully."""
        
        sns_success = send_sns_notification("Processing Completed", success_message, success=True)
        
        # Save and cleanup logs
        logs_success = save_logs_to_s3(log_filename)
        
        # Cleanup local JSON files after successful S3 upload
        json_cleanup_success = cleanup_local_json_files(time_period)
        
        return s3_success and sns_success and logs_success and json_cleanup_success
        
    except Exception as e:
        logging.error(f"Error in cleanup and notification: {e}")
        return False


def handle_error_and_notify(error: Exception, time_period: str, log_filename: str) -> None:
    """Handle errors: send error notifications and cleanup logs."""
    try:
        # Send error notification
        error_message = f"""Gmail processing failed!
        
Time Period: {time_period}
Error Details: {str(error)}
        
Please check the logs in S3 for more details.
System will attempt to save logs before shutdown."""
        
        send_sns_notification("Processing Failed", error_message, success=False)
        
        # Try to save logs even on error
        save_logs_to_s3(log_filename)
        
        # Try to cleanup local JSON files even on error to prevent accumulation
        cleanup_local_json_files(time_period)
        
    except Exception as e:
        logging.error(f"Error in error handling: {e}")