# Gmail Organizer Configuration
import os

# API Keys and Credentials
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/'
OPENAI_API_KEY = "sk-proj-k1GTgA"
AWS_ACCESS_KEY_ID = 'AK'
AWS_SECRET_ACCESS_KEY = 'm'

# Set environment variables
os.environ['SLACK_WEBHOOK_URL'] = SLACK_WEBHOOK_URL
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY

# LLM Provider Selection
LLM_PROVIDER = 'ollama'  # Options: 'bedrock', 'ollama', 'openai'

# AWS Configuration
AWS_REGION = 'us-east-1'
BEDROCK_REGION = 'us-east-1'
MODEL_ID = 'us.meta.llama3-3-70b-instruct-v1:0'

# AWS S3 Configuration
S3_BUCKET = 'gmail-organizer'
S3_LOGS_PREFIX = 'logs/'
S3_SUMMARIES_PREFIX = 'summaries/'

# AWS SNS Configuration  
SNS_TOPIC_ARN = "arn:aws:sns:us-east-"

# Ollama Configuration
OLLAMA_BASE_URL = 'http://localhost:11434'
OLLAMA_MODEL = 'llama3.1:latest'

# OpenAI Configuration  
OPENAI_MODEL = 'gpt-4o-mini'

# Gmail API Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

# Email Classification - 3 Categories + Skip Option
EMAIL_LABELS = ['urgent', 'important', 'promotions', 'skip']
PRIORITY_LEVELS = ['high', 'medium', 'low']
THREAD_STATUS = ['needs-reply', 'follow-up', 'closed']
POSSIBLE_ACTIONS = ['apply_label', 'draft_response']


# Label Colors for Gmail - Using Gmail's predefined color palette
LABEL_COLORS = {
    'urgent': {
        'backgroundColor': '#cc3a21',     # Gmail's predefined red
        'textColor': '#ffffff'
    },
    'important': {
        'backgroundColor': '#ffad47',     # Gmail's predefined orange
        'textColor': '#ffffff'  
    },
    'promotions': {
        'backgroundColor': '#666666',     # Gmail's predefined grey
        'textColor': '#ffffff'
    }
}