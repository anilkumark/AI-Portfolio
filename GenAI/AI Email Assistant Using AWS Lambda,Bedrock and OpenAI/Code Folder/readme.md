# Execution Instructions

## Python version 3.12

To create a virtual environment and install requirements in Python 3.12 on different operating systems, follow the instructions below:

### For Windows:

Open the Command Prompt by pressing `Win + R`, typing `cmd`, and pressing `Enter`.

Change the directory to the desired location for your project:

```sh
cd C:\path\to\project
```

Create a new virtual environment using the `venv` module:

```sh
python -m venv myenv
```

Activate the virtual environment:

```sh
myenv\Scripts\activate
```

Install the project requirements using pip:

```sh
pip install -r requirements.txt
```

### For Linux/Mac:

Open a terminal.

Change the directory to the desired location for your project:

```sh
cd /path/to/project
```

Create a new virtual environment using the `venv` module:

```sh
python3.12 -m venv myenv
```

Activate the virtual environment:

```sh
source myenv/bin/activate
```

Install the project requirements using pip:

```sh
pip install -r requirements.txt
```

These instructions assume you have Python 3.12 installed and added to your system's `PATH` variable.

## Execution Instructions if Multiple Python Versions Installed

If you have multiple Python versions installed on your system, you can use the Python Launcher to create a virtual environment with Python 3.12. Specify the version using the `-p` or `--python` flag. Follow the instructions below:

### For Windows:

Open the Command Prompt by pressing `Win + R`, typing `cmd`, and pressing `Enter`.

Change the directory to the desired location for your project:

```sh
cd C:\path\to\project
```

Create a new virtual environment using the Python Launcher:

```sh
py -3.12 -m venv myenv
```

> **Note**: Replace `myenv` with your desired virtual environment name.

Activate the virtual environment:

```sh
myenv\Scripts\activate
```

Install the project requirements using pip:

```sh
pip install -r requirements.txt
```

### For Linux/Mac:

Open a terminal.

Change the directory to the desired location for your project:

```sh
cd /path/to/project
```

Create a new virtual environment using the Python Launcher:

```sh
python3.12 -m venv myenv
```

> **Note**: Replace `myenv` with your desired virtual environment name.

Activate the virtual environment:

```sh
source myenv/bin/activate
```

Install the project requirements using pip:

```sh
pip install -r requirements.txt
```

By specifying the version using `py -3.12` or `python3.12`, you can ensure that the virtual environment is created using Python 3.12 specifically, even if you have other Python versions installed.


# Gmail AI Organizer - Complete Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Gmail API Setup](#gmail-api-setup)
3. [Slack Integration Setup](#slack-integration-setup)
4. [AWS Infrastructure Setup](#aws-infrastructure-setup)
5. [AI Provider Configuration](#ai-provider-configuration)
6. [EC2 Instance Creation and Setup](#ec2-instance-creation-and-setup)
7. [Lambda Function for Automation](#lambda-function-for-automation)
8. [Code Deployment](#code-deployment)
9. [Cron Job Configuration](#cron-job-configuration)
10. [Ollama GPU Setup (Optional)](#ollama-gpu-setup-optional)
11. [Testing and Monitoring](#testing-and-monitoring)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

- AWS Account with billing enabled
- Gmail account with administrative access
- Slack workspace with app creation permissions
- Local development environment (Mac/Windows)
- Basic knowledge of command line operations

## Gmail API Setup

### Step 1: Enable Gmail API in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to "APIs & Services" → "Library"
4. Search for "Gmail API" and click "Enable"
5. Go to "APIs & Services" → "Credentials"
6. Click "Create Credentials" → "OAuth client ID"
7. Configure consent screen:
   - User Type: External  or Internal (for G Suite)
   - App name: "Gmail AI Organizer"
   - Support email: Your email
   - Developer email: Your email
8. Create OAuth client ID:
   - Application type: Desktop application
   - Name: "Gmail Organizer Desktop"
9. Download the JSON file and rename it to `credentials.json`
10. Place `credentials.json` in your project root directory

### Step 2: Gmail API Permissions

Ensure your OAuth client has these scopes:
- `https://www.googleapis.com/auth/gmail.modify`

The first time you run the application, it will open a browser window for OAuth consent.

## Slack Integration Setup

### Step 1: Create Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. App Name: "Gmail AI Organizer"
4. Choose your workspace
5. Go to "Incoming Webhooks" in the left sidebar
6. Toggle "Activate Incoming Webhooks" to ON
7. Click "Add New Webhook to Workspace"
8. Choose the channel where you want notifications
9. Copy the webhook URL (starts with `https://hooks.slack.com/services/`)

### Step 2: Configure Webhook

Add the webhook URL to your configuration- config.py:
```
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## AWS Infrastructure Setup

### Step 1: Create IAM User

1. Go to AWS Console → IAM → Users
2. Click "Add users"
3. Username: `gmail-organizer-user`
4. Access type: Programmatic access
5. Attach policies directly:
   - `AmazonEC2FullAccess`
   - `AmazonS3FullAccess`
   - `AmazonSNSFullAccess`
   - `AWSLambdaFullAccess`
   - For Bedrock: `AmazonBedrockFullAccess`
6. Download access keys (CSV file)
7. Configure AWS on config.py

### Step 2: Create S3 Bucket

1. Go to AWS Console → S3
2. Click "Create bucket"
3. Bucket name: `gmail-organizer-data`
4. Region: `us-east-1`
5. Keep default settings (private bucket)
6. Click "Create bucket"

### Step 3: Create SNS Topic

1. Go to AWS Console → SNS
2. Click "Create topic"
3. Type: Standard
4. Name: `gmail-organizer-notifications`
5. Click "Create topic"
6. Click "Create subscription"
7. Protocol: Email
8. Endpoint: Your email address
9. Confirm subscription via email
10. Note the Topic ARN for configuration in config.py

### Step 4: AWS Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock
2. Click "Model access" in left sidebar
3. Click "Request model access"
4. Select "Meta" → "Llama 3.3 70B Instruct"
5. Submit request (may take 24-48 hours for approval)

## AI Provider Configuration

### OpenAI Setup

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create account or sign in
3. Go to API Keys section
4. Create new secret key
5. Copy the key (starts with `sk-proj-`)
6. Add to config.py:


### Ollama Setup (Local Development)

#### macOS Installation:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull llama3.1:latest

# Start Ollama server
ollama serve
```

#### Windows Installation:
1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Run the installer
3. Open Command Prompt or PowerShell
4. Pull model: `ollama pull llama3.1:latest`
5. Start server: `ollama serve`

## EC2 Instance Creation and Setup

### Step 1: Create Key Pair

1. Go to AWS Console → EC2 → Key Pairs
2. Click "Create key pair"
3. Name: `gmail-organizer-key`
4. Type: RSA, Format: .pem
5. Download and save securely
6. Set permissions (Mac/Linux):
   ```bash
   chmod 400 gmail-organizer-key.pem
   mv gmail-organizer-key.pem ~/.ssh/
   ```
If you’re on Windows, right-click the .pem file, go to Properties, then Security, and remove all users except your administrator account. This ensures the key has the right restricted permissions for SSH.

### Step 2: Create Security Group

1. Go to EC2 → Security Groups
2. Click "Create security group"
3. Name: `gmail-organizer-sg`
4. Description: "Security group for Gmail organizer"
5. Inbound rules:
   - SSH (22): 0.0.0.0
   - For Ollama: Custom TCP (11434): My IP or 0.0.0.0
6. Outbound rules: All traffic (default)

### Step 3: Launch EC2 Instance

#### For CPU-only processing (Bedrock/OpenAI):
1. Go to EC2 → Instances → Launch Instance
2. Name: `gmail-organizer-cpu`
3. AMI: Ubuntu Server 22.04 LTS
4. Instance type: `t2.micro` (free tier) or `t3.small`
5. Key pair: `gmail-organizer-key`
6. Security group: `gmail-organizer-sg`
7. Storage: 8 GB gp3
8. Launch instance

#### For GPU processing (Ollama):
1. Go to EC2 → Instances → Launch Instance
2. Name: `gmail-organizer-gpu`
3. AMI: Ubuntu Server 22.04 LTS
4. Instance type: `g4dn.xlarge` or `g5.large`
5. Key pair: `gmail-organizer-key`
6. Security group: `gmail-organizer-sg`
7. Storage: 20 GB gp3
8. Launch instance

## Lambda Function for Automation

### Step 1: Create Lambda Function

1. Go to AWS Console → Lambda
2. Click "Create function"
3. Function name: `gmail-organizer-ec2-starter`
4. Runtime: Python 3.12
5. Create new role with basic Lambda permissions and ec2 access

### Step 2: Lambda Function Code

Replace default code with:
```python
import boto3
import json

# Configuration - Replace with your instance ID
region = 'us-east-1'
instances = ['i-0']  # Your EC2 instance ID
ec2 = boto3.client('ec2', region_name=region)

def lambda_handler(event, context):
    try:
        # Start the EC2 instances
        response = ec2.start_instances(InstanceIds=instances)
        
        print(f'Successfully started instances: {instances}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully started instances: {instances}',
                'response': response
            })
        }
        
    except Exception as e:
        print(f'Error starting instances: {str(e)}')
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Failed to start instances: {str(e)}',
                'instances': instances
            })
        }
```

### Step 3: Update Lambda IAM Role

1. Go to IAM → Roles
2. Find the Lambda execution role
3. Attach EC2FullAccess

### Step 4: Create EventBridge Rules

Create three rules for daily schedule:

#### Morning Rule (9 AM IST = 3:30 AM UTC):
1. Go to EventBridge → Rules → Create rule
2. Name: `gmail-organizer-morning`
3. Schedule: `30 3 * * ? *`
4. Target: Lambda function `gmail-organizer-ec2-starter`

#### Afternoon Rule (2 PM IST = 8:30 AM UTC):
1. Name: `gmail-organizer-afternoon`
2. Schedule: `30 8 * * ? *`
3. Target: Same Lambda function

#### Evening Rule (5 PM IST = 2:30 PM UTC):
1. Name: `gmail-organizer-evening`
2. Schedule: `30 14 * * ? *`
3. Target: Same Lambda function

## Code Deployment

### Step 1: Prepare Local Code

1. Update `src/config.py` with your settings:
```python
# API Keys and Credentials
SLACK_WEBHOOK_URL = 'your-webhook-url'
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
OPENAI_API_KEY = 'your-openai-key'  # if using OpenAI

# AWS Configuration
AWS_REGION = 'us-east-1'
S3_BUCKET = 'your-bucket-name'
SNS_TOPIC_ARN = 'your-sns-topic-arn'

# LLM Provider Selection
LLM_PROVIDER = 'bedrock'  # or 'openai' or 'ollama'
```

### Step 2: Copy Code to EC2

Replace the paths with your actual values:
```bash
# Copy entire project to EC2
scp -i ~/.ssh/gmail-organizer-key.pem -r /path/to/gmail-organizer ubuntu@your-ec2-ip:/home/ubuntu/gmail-organizer

# Example:
scp -i ~/.ssh/gmail-organizer-key.pem -r /Users/yourname/gmail-organizer ubuntu@ec2-15-206-158-29.ap-south-1.compute.amazonaws.com:/home/ubuntu/gmail-organizer
```

### Step 3: SSH into EC2 and Setup Environment

```bash
# Connect to EC2
ssh -i ~/.ssh/gmail-organizer-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 venv 
sudo apt install python3.12-venv 

# Navigate to project directory
cd /home/ubuntu/gmail-organizer

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```


## Cron Job Configuration

### Setup Cron Jobs for All Three Times

```bash
# Edit cron jobs
crontab -e

# Add these lines (5-minute buffer after Lambda starts instance):
# Morning run - 9:05 AM IST (3:35 AM UTC)
35 3 * * * cd /home/ubuntu/gmail-organizer && /home/ubuntu/gmail-organizer/venv/bin/python3 main.py >> /home/ubuntu/gmail-organizer/main.log 2>&1

# Afternoon run - 2:05 PM IST (8:35 AM UTC)  
35 8 * * * cd /home/ubuntu/gmail-organizer && /home/ubuntu/gmail-organizer/venv/bin/python3 main.py >> /home/ubuntu/gmail-organizer/main.log 2>&1

# Evening run - 5:05 PM IST (2:35 PM UTC)
35 14 * * * cd /home/ubuntu/gmail-organizer && /home/ubuntu/gmail-organizer/venv/bin/python3 main.py >> /home/ubuntu/gmail-organizer/main.log 2>&1

# Save and exit (Ctrl+X, Y, Enter)
```

### Restart Cron Service

```bash
sudo service cron restart

# Verify cron jobs
crontab -l

# Check cron logs
sudo tail -f /var/log/syslog | grep CRON
```

## Ollama GPU Setup and Exposing Outside EC2 (Optional)

### Step 1: Create GPU-Enabled EC2 Instance

Use `g4dn.xlarge` or `g5.large` instance with the setup above.

### Step 2: Install NVIDIA Drivers

```bash
# Connect to GPU instance
ssh -i ~/.ssh/gmail-organizer-key.pem ubuntu@your-gpu-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install NVIDIA drivers
sudo apt install -y nvidia-driver-535 nvidia-utils-535

# Reboot system
sudo reboot

# Reconnect and verify GPU
nvidia-smi
```

### Step 3: Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.1:latest

# Configure Ollama to accept external connections
sudo systemctl edit ollama

# Add these lines in the editor:
[Service]
Environment="OLLAMA_HOST=0.0.0.0"

# Save and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama
```



### Step 4: Update Security Group

Add inbound rule for TCP port 11434 from your IP address only or can set anywhere 0.0.0.0 for testing.

## Testing and Monitoring

### Step 1: Manual Test

```bash
# SSH into EC2
ssh -i ~/.ssh/gmail-organizer-key.pem ubuntu@your-ec2-ip

# Activate environment and run
cd /home/ubuntu/gmail-organizer
source venv/bin/activate
python3 main.py
```

### Step 2: Check Logs

```bash
# View application logs
tail -f /home/ubuntu/gmail-organizer/main.log

# View system logs
sudo tail -f /var/log/syslog

# View cron logs
sudo tail -f /var/log/cron.log
```

### Step 3: Monitor AWS Resources

1. **CloudWatch Logs**: Monitor Lambda execution
2. **S3 Bucket**: Check for uploaded summaries and logs
3. **SNS**: Verify notifications are being sent
4. **EC2**: Monitor instance start/stop cycles

## Troubleshooting

#### Cron Job Issues:
```bash
# Check cron status
sudo systemctl status cron

# View cron logs with more detail
sudo journalctl -u cron -f
```

#### Ollama Issues:
```bash
# Check Ollama status
sudo systemctl status ollama

# View Ollama logs
sudo journalctl -u ollama -f

# Test GPU usage
nvidia-smi -l 1  # Real-time GPU monitoring
```
