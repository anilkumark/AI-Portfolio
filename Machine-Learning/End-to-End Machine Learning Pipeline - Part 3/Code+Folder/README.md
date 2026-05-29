# E2E Part 3
## Overview
The project addresses a critical challenge faced by the logistics industry. Delayed truck shipments not only result in increased operational costs but also impact customer satisfaction. Timely delivery of goods is essential to meet customer expectations and maintain the competitiveness of logistics companies.
By accurately predicting truck delays, logistics companies can:
Improve operational efficiency by allocating resources more effectively
Enhance customer satisfaction by providing more reliable delivery schedules
Optimize route planning to reduce delays caused by traffic or adverse weather conditions
Reduce costs associated with delayed shipments, such as penalties or compensation to customers



Approach
* Setting up Streaming Data Generation:
   * Define functions or scripts to generate streaming data mimicking real-world scenarios
   * Ensure data is representative and diverse to capture various conditions and events
* Lambda Function Creation for Streaming Data:
   * Write Lambda function code to handle incoming streaming data
   * Configure necessary permissions and triggers for Lambda execution
   * Develop Lambda function logic to process and transform streaming data
   * Integrate Lambda functions into the pipeline architecture for seamless data flow
* Docker Image Creation with Python 3.10:
   * Build a Docker image containing the required Python environment and dependencies
* Streaming Data Integration and Pipeline Monitoring:
   * Implement mechanisms for monitoring pipeline, performance, and data quality
* Data Drift and Model Drift Calculation:
   * Implement algorithms to calculate data drift and model drift based on historical and real-time data
   * Monitor deviations in data and model performance for proactive intervention
* Model Retraining and Evaluation:
   * Develop processes for retraining models based on detected drift and updated data
* Scenario-based Runs and Testing:
   * Perform scenario-based runs to simulate different operational conditions and scenarios
   * Scheduling SageMaker Pipeline Execution
   * Configure scheduling mechanisms to automate the execution of SageMaker pipelines at predefined intervals
* Notification System Setup and Implementation:
   * Configure notification systems to provide alerts and updates on pipeline status and events
   * Integrate notification systems into the pipeline architecture for effective communication and monitoring
* Resource Cleanup Post-execution:
   * Ensure efficient resource management and cost optimization by removing unused or unnecessary resources
* Conclusion:
   * Summarize key findings, insights, and outcomes from the monitoring approach


```
E2E-3 Codes
├─ Lambda_function_streaming_data
│  ├─ lambda_layers
│  │  ├─ pymysql_layer.zip
│  │  └─ sqlalchemy_psycopg2_layer.zip
│  └─ lambda_streaming_data_gen.py
├─ Python3.10_docker
│  └─ Dockerfile
├─ README.md
├─ sagemaker_pipeline_notifications_cdk
│  └─ python
│     ├─ app.py
│     ├─ cdk.json
│     ├─ Dockerfile
│     ├─ example-workflow.json
│     ├─ lambda_function.py
│     ├─ requirements.txt
│     ├─ resources
│     │  ├─ sample-event.json
│     │  └─ statemachine.png
│     └─ source.bat
├─ StreamingData_Sagemaker_Pipeline
│  ├─ calculate_data_drift.py
│  ├─ calculate_model_drift.py
│  ├─ feature_engg_finalmerge_hopsworks.py
│  ├─ fetch_streaming_dump_to_hopsworks.py
│  ├─ is_first_day_of_week.py
│  ├─ model_drift_not_detected.py
│  ├─ model_retraining.py
│  ├─ not_first_day_of_week.py
│  ├─ pipeline-structure.png
│  ├─ pipeline.py
│  ├─ previous_data_updation.py
│  ├─ sagemaker-pipelines-project.ipynb
│  └─ test.py
├─ Streaming_data
│  ├─ streaming_city_weather.csv
│  ├─ streaming_route_weather.csv
│  ├─ streaming_schedule.csv
│  └─ streaming_traffic.csv
└─ Training_Codes
   ├─ app.py
   ├─ config.yaml
   ├─ data
   │  ├─ Database_backup
   │  │  ├─ truck-eta-mysql.sql
   │  │  └─ truck-eta-postgres.sql
   │  ├─ data_description.pdf
   │  └─ Training_data
   │     ├─ city_weather.csv
   │     ├─ drivers_table.csv
   │     ├─ routes_table.csv
   │     ├─ routes_weather.csv
   │     ├─ traffic_table.csv
   │     ├─ trucks_table.csv
   │     └─ truck_schedule_table.csv
   ├─ engine.py
   ├─ logs
   │  ├─ truck_eta_error_logs.log
   │  └─ truck_eta_info_logs.log
   ├─ ml_pipeline
   │  ├─ data_prep.py
   │  ├─ evaluate.py
   │  ├─ modelling.py
   │  ├─ process.py
   │  └─ utils.py
   ├─ models
   │  ├─ log-truck-model.pkl
   │  ├─ randomf-truck-model.pkl
   │  └─ xgb-truck-model.pkl
   ├─ notebooks
   │  ├─ Truck-Delay-Classification_Part_2.ipynb
   │  └─ Truck_Delay_Classification_Part_1.ipynb
   ├─ output
   │  ├─ truck_data_encoder.pkl
   │  └─ truck_data_scaler.pkl
   ├─ requirements.txt
   └─ sample-monitoring_pipeline.ipynb

```

Here is a brief information on the folders:
Lambda Function for Streaming Data: Contains lambda functions and required layers for streaming data, including lambda_streaming_data_gen.py and zipped Python layers (pymysql_layer.zip and sqlalchemy_psycopg2_layer.zip).


Docker Setup: Provides a Dockerfile for setting up a Python 3.10 environment, located in the Python3.10_docker directory.


SageMaker Pipeline Notifications CDK: Includes scripts and configurations for SageMaker pipeline notifications using CDK, located in the sagemaker_pipeline_notifications_cdk/python directory, with key files like app.py, lambda_function.py, and cdk.json.


Streaming Data SageMaker Pipeline: Contains scripts, Jupyter notebooks, and other resources for the streaming data SageMaker pipeline, found in the StreamingData_Sagemaker_Pipeline directory, with files like pipeline.py, calculate_data_drift.py, and sagemaker-pipelines-project.ipynb.


Training Codes: Includes all the necessary scripts, data, and configurations for training models, located in the Training_Codes directory. Key components include training data (Training_data), database backups (Database_backup), machine learning pipeline scripts (ml_pipeline), trained models (models), and notebooks for analysis (notebooks).


# Local Execution Instructions

# Python version 3.10

To create a virtual environment and install requirements in Python 3.10 on different operating systems, follow the instructions below:

### For Windows:

Open the Command Prompt by pressing Win + R, typing "cmd", and pressing Enter.

Change the directory to the desired location for your project:


`cd C:\path\to\project`

Create a new virtual environment using the venv module:


`python -m venv myenv`

Activate the virtual environment:

`myenv\Scripts\activate`


Install the project requirements using pip:

`pip install -r requirements.txt`

### For Linux/Mac:
Open a terminal.

Change the directory to the desired location for your project:

`cd /path/to/project`

Create a new virtual environment using the venv module:

`python3.10 -m venv myenv`


Activate the virtual environment:

`source myenv/bin/activate`

Install the project requirements using pip:

`pip install -r requirements.txt`

These instructions assume you have Python 3.10 installed and added to your system's PATH variable.

## Execution Instructions if Multiple Python Versions Installed

If you have multiple Python versions installed on your system, you can use the Python Launcher to create a virtual environment with Python 3.10. Specify the version using the -p or --python flag. Follow the instructions below:

For Windows:
Open the Command Prompt by pressing Win + R, typing "cmd", and pressing Enter.

Change the directory to the desired location for your project:

`cd C:\path\to\project`

Create a new virtual environment using the Python Launcher:

`py -3.10 -m venv myenv`

Note: Replace myenv with your desired virtual environment name.

Activate the virtual environment:

`
myenv\Scripts\activate
`

Install the project requirements using pip:

`pip install -r requirements.txt`


### For Linux/Mac:
Open a terminal.

Change the directory to the desired location for your project:

`cd /path/to/project
`
Create a new virtual environment using the Python Launcher:


`python3.10 -m venv myenv`


Note: Replace myenv with your desired virtual environment name.

Activate the virtual environment:

`source myenv/bin/activate`

Install the project requirements using pip:

`pip install -r requirements.txt`


By specifying the version using py -3.10 or python3.10, you can ensure that the virtual environment is created using Python 3.10 specifically, even if you have other Python versions installed.



## Run streamlit application

`streamlit run app.py`



# Streamlit Application Deployment on AWS EC2

## Overview

This guide provides step-by-step instructions for deploying a Streamlit application on an AWS EC2 instance. 

## Prerequisites

- AWS Account
- Basic knowledge of AWS EC2, SSH, and Streamlit


## Deployment Steps

### 1. Launching EC2 Instance

- Launch an EC2 instance on AWS with the following specifications:
  - Ubuntu 22.04 LTS
  - Instance Type: t2.medium (or your preferred type)
  - Security Group: Allow inbound traffic on port 8501 for Streamlit

- Create and download a PEM key for SSH access to the EC2 instance.

- Disable Inheritance and Restrict Access on PEM key For Windows Users:
    - Locate the downloaded PEM key file (e.g., your-key.pem) using File Explorer.

    - Right-click on the PEM key file and select "Properties."

    - In the "Properties" window, go to the "Security" tab.

    - Click on the "Advanced" button.

    - In the "Advanced Security Settings" window, you'll see an "Inheritance" section. Click on the "Disable inheritance" button.

    - A dialog box will appear; choose the option "Remove all inherited permissions from this object" and click "Convert inherited permissions into explicit permissions on this object."

    - Once inheritance is disabled, you will see a list of users/groups with permissions. Remove permissions for all users except for the user account you are using (typically an administrator account).

    - Click "Apply" and then "OK" to save the changes.


### 2. Accessing EC2 Instance

1. Use the following SSH command to connect to your EC2 instance:
  ```
  ssh -i "your-key.pem" ubuntu@your-ec2-instance-public-ip
  ```

2. Gain superuser access by running: `sudo su`

3. Updating and Verifying Python
  - Update the EC2 instance with the latest packages:
    `apt update`

  - Verify Python installation:
    `python3 --version`

4. Installing Python Packages
`apt install python3-pip`

5. Transferring Files to EC2
    Use SCP to transfer your Streamlit application code to the EC2 instance:

    ```scp -i "your-key.pem" -r path/to/your/app ubuntu@your-ec2-instance-public-ip:/path/to/remote/location```

6. Setting Up Streamlit Application
    Change the working directory to the deployment files location:

    `cd /path/to/remote/location`

    Install dependencies from your requirements file:

    `pip3 install -r requirements.txt`

7. Running the Streamlit Application
    Test your Streamlit application (Use external link):
    `streamlit run app.py`


    For a permanent run, use nohup:
    `nohup streamlit run app.py`

8. Cleanup and Termination
To terminate the nohup process:
  - `sudo su`
  - `ps -df`
  - `kill {process id}`


# SCRIPT FOR CONSTANTS TABLE
create table constants(id int, routes_weather bigint,
						truck_schedule_data bigint,
						traffic_details bigint,
						city_weather bigint,
					   	is_first_day_of_new_week boolean,
						week_start_date date,
					    day date,
					  	weekly_streaming bigint);
						
# Insert the data
insert into constants values(1, 425712, 12308, 2597913, 55176, False, '2019-02-15', '2019-02-15', 1);