# Introduction
The objectives of the project are defined in Project Proposal pdf and requirements for the repository are in the txt file.

# Folder Structure
1. The folder `src/helper.py` contains all the modular functions needed in the project. 
2. `analysis.ipynb` notebook performs data analysis and EDA and also allows programmer to run the code. 
3. Setup the `OpenAI key` as highlighted in the code and [here](https://platform.openai.com/docs/quickstart) in the enviroment variables. Put it on line 11 in `helper.py`.
3. `demo.py` contains the streamlit demo code. To run it, go to the terminal and enter `streamlit run demo.py` and follow the instructions.
4. The folder `vector_store` contains the FAISS database of the datset which is vectorized and stored and helps in the RAG pipeline process.


```

├─ Customer_Support_Training_Dataset
│  └─ Customer_Support_Training_Dataset.csv
|  └─ dataset.md
├─ analysis.ipynb
├─ README.md
├─ demo.py
├─ src
│  └─ helper.py
├─ vector_store
│  └─ faiss_index.index
├─ requirements.txt

```

## Getting Started
1. After installing the packages, setup your OpenAI key in the enviroment. `helper.py` contains function `call_llm` which calls OpenAI API. So, put your OpenAI key in `helper.py` or you can also use environment variable.
2. Embeddings are created and stored as FAISS index. To create embeddings, see the `analysis.ipynb`. Else, to get started quickly, just load the stored FAISS index.


## Prerequisites
Python 3.10 must be installed.
Ensure you have access to the required datasets and connection strings for databases.


### Steps for running the project locally

## Steps to Run

There are two ways to execute the end to end flow.

- Modular Code (analysis.ipynb)
- IPython

The Python 3.10 version is supported for the execution of this project.
1. Running the codes locally: Python 3.10
    - Create a virtual environment: In the terminal or command prompt, use the following command to create a new virtual environment:

        - For Windows:
            `py -3.10 -m venv env`

        - For macOS and Linux:
            `python3 -m venv venv`
        This command creates a new virtual environment named "venv" in the current directory.

    - Activate the virtual environment:

        - For Windows (Command Prompt):
            `venv\Scripts\activate`


        - For macOS and Linux (Terminal) :
            `source venv/bin/activate`
    
Once the virtual environment is activated, you should see the environment name (e.g., (venv)) in the terminal or command prompt.

- Install project requirements: With the virtual environment active, you can now install the required packages for your project. Typically, the required packages are listed in a requirements.txt file. Make sure you have the requirements.txt file for your project.

2. Setup the pip and installing dependencies in Virtual environment

    - Upgrade pip
        `python -m pip install --upgrade pip`

    - To install the requirements, use the following command:
        `pip install -r requirements.txt`
        
## **Execution Instructions**

* Install the requirements using the command 'pip install -r requirements.txt'
* Select the virtual environment you created as the kernel to run the analysis.ipynb notebook.


#### Project Execution
- Run the CUSTOMER-SUPPORT application using Streamlit:
- Add API Key in helper

`streamlit run demo.py`

Access the application:

After running the command, the app will open automatically in your default browser. If not, navigate to the provided local URL (usually http://localhost:8501/) to access the application.



## Step-by-Step Procedure to execute project on Azure

### Creating Azure DevOps Organization and Azure Repos

This project uses Azure Repos as the version control system for managing the project codebase, tracking changes, collaboration, and Azure service integrations.

Azure Repos works similarly to GitHub and provides seamless integration with Azure services such as Azure ML, Azure App Services, and deployment pipelines.

Step 1: Create Azure DevOps Organization

- Open the Azure Portal.
- In the search bar, search for Azure DevOps.
- Open Azure DevOps.
- Click on Create Organization.
- Enter the organization name and select the region.
- Click Continue.

Step 2: Create a New Azure DevOps Project

- Inside Azure DevOps, click on New Project.
- Enter the project name.
- Optionally add a project description.
- Select the visibility type.
- Click Create.

Step 3: Create Azure Repos Repository

- From the left-side panel, open Repos.
- Azure Repos repository will be created automatically for the project.
- Click on Clone and copy the HTTPS repository URL.


Azure Repos will act as the centralized version control system for this project.

#### Push Local Project Files to Azure Repos

Open the project folder in VS Code and open the terminal.

Step 1: Initialize Git Repository
- `git init`

This command initializes Git inside the project directory.

Step 2: Add All Project Files
- `git add .`

This command stages all files and folders for tracking.

Step 3: Commit the Files
- `git commit -m "Initial Commit"`

This creates the first project snapshot in the version control system.

Step 4: Connect Local Project to Azure Repos
- `git remote add origin <AZURE_REPO_URL>`

Replace <AZURE_REPO_URL> with the HTTPS URL copied from Azure Repos.

This step connects the local project directory to Azure Repos.

Step 5: Rename Branch to Main
 - `git branch -M main`

This renames the default branch to main.

Step 6: Push Files and Folders to Azure Repos
- `git push -u origin main`

This uploads all project files and folders from the local system to Azure Repos.

After successful execution, refresh Azure Repos in Azure DevOps to verify that all files and folders are uploaded successfully.


### Azure ML Workspace Setup

Azure Machine Learning Workspace is used in this project for executing notebooks, managing environments, running AI workflows, and deploying machine learning applications.

The Azure ML Workspace acts as the central environment for developing and managing the AI Customer Support Automation System.

Step 1: Open Azure Portal

- Open the Azure Portal.
- In the search bar, search for Azure Machine Learning.
- Open the Azure Machine Learning service.
- Step 2: Create Azure ML Workspace
- Click on Create.
- Select Azure Machine Learning.
- Click Create again.

Now provide the required details:

- Subscription → Select your Azure subscription
- Resource Group → Create a new resource group or select an existing one
- Workspace Name → Enter the workspace name
- Region → Select the preferred region
- Storage Account → Leave default or create new
- Key Vault → Leave default
- Application Insights → Leave default
- Container Registry → Leave default

After filling the details, click:

- Review + Create
- Then click:
- Create

Azure will now start deploying the Azure ML Workspace.

Step 3: Open Azure ML Studio

- Once deployment is completed:

Open the created Azure ML Workspace.
- Click on:Launch Studio

Azure ML Studio will now open. This is the main interface where notebooks, compute instances, environments, datasets, and deployments are managed.

Step 4: Create Compute Instance

The compute instance is required to execute notebooks and run the project code. Inside Azure ML Studio:

- Go to the left panel.
- Open: Compute
- Click on: Compute Instances
- Click: New

Now configure:

- Compute name
- Virtual machine size
- Region

Recommended:

- Select a small CPU instance for basic execution and testing

- Click: Create

The compute instance may take a few minutes to start.

Step 5: Open Notebook Environment

- After the compute instance is running:

- Go to: Notebooks and Open the terminal or notebook interface.

This environment will be used to:

- Clone Azure Repos
- Run notebooks
- Install dependencies
- Execute Streamlit applications
- Perform RAG workflows

Step 6: Clone Azure Repos inside Azure ML

- Inside the terminal, run:

- `git clone <AZURE_REPO_URL>`

This downloads the complete project repository into the Azure ML environment.

Step 7: Navigate to the Project Folder
- cd Project_Modular_Code

Replace the folder name with your actual repository folder name if needed.

Step 8: Verify the Default Python Version in Azure ML

After navigating to the project folder, check the default Python version available inside the Azure ML terminal:

python --version

or

python3 --version

In current Azure ML environments, the default runtime already uses Python 3.10.

Since Python 3.10 is compatible with the project requirements and current package versions, there is no need to create a separate virtual environment inside Azure ML in most cases.

Step 8: Install Project Dependencies
- `pip install -r requirements.txt`

This installs all required packages and libraries for the project.

Step 9: Select the Correct Kernel

While running the notebook:

- Select the virtual environment or Python kernel where the dependencies are installed. Use the created environment as the kernel for running analysis.ipynb.


Step 10: Run the Streamlit Application

To run the Streamlit application:

- `streamlit run demo.py --server.port 8501 --server.address 0.0.0.0 --browser.serverAddress 0.0.0.0`

This starts the AI Customer Support Automation application inside Azure ML.


Step 11: Access the Streamlit Application from Azure ML

To access the Streamlit application:

- Copy the compute instance URL in the following format:

- `<compute-name>.<region>.instances.azureml.ms`

Example:

The region used in the URL should be the same region where your Azure ML Workspace and compute instance are created.

Example format:

- `https://<compute-name>.<region>.instances.azureml.ms:8501`

If your Azure ML Workspace is created in the East US region, then the compute instance URL will also contain the same region information.

Example:

- `https://cpu-instance.eastus.instances.azureml.ms:8501`

Since the Streamlit application is running inside the Azure ML compute instance, the application can be accessed directly using the Azure ML compute endpoint.


### Deployment of Streamlit Application on Azure App Service

Deploying the Streamlit Application on Azure App Service

1. Now that the Streamlit application has been developed and tested successfully inside the Azure ML environment, the next step is to deploy the application on Azure App Services so that it can be accessed publicly through a web URL.

2. Azure App Service helps host and deploy web applications directly from Azure Repos with built-in deployment and scaling support.

3. The deployment process explained below uses Azure Repos as the source repository for automatic deployment and version control.


#### Azure App Service Deployment Workflow

The deployment flow is:

Local System → Azure Repos → Azure App Service → Public Streamlit Application

This setup helps in:

- centralized deployment,
- easier updates,
- version control,
- scalability,
- and production-style hosting workflows.

#### Prerequisites

Before starting deployment, ensure the following are completed:

- Azure ML Workspace setup completed
- Azure Repos repository created
- Project files pushed to Azure Repos
- Streamlit application tested locally or inside Azure ML
- requirements.txt file available
- demo.py available in the root project directory


Step 1: Open Azure App Services

- Open the Azure Portal.
- In the search bar, search for: App Services
- Open Azure App Services.

Step 2: Create a New Web App
- Click on: Create
- Select: Web App

Now configure the following settings:

- Subscription
- Resource Group
- App Name
- Publish → Code
- Runtime Stack → Python 3.10
- Operating System → Linux
- Region → Select preferred region
- Pricing Plan → Basic or appropriate plan

### Note:
Older videos may mention Python 3.9 runtime. Currently Python 3.10 is recommended because newer Azure runtimes and dependencies work more reliably with Python 3.10.

After filling the details:

- Click: Review + Create
- Then click: Create

Azure will now start deploying the Azure App Service resources.

Step 3: Open the Created Web App

After deployment is completed:

- Open the created Web App resource.
- Wait for all resources to load properly.


Step 4: Configure Deployment Source
The application code still needs to be connected to Azure App Service. To configure deployment:

- From the left panel, open: Deployment Center
- Under Source, select: Azure Repos
- Select: Organization
- Project: Repository
- Branch (main)

Step 5: Enable SCM Basic Authentication

If Azure shows the message:

SCM Basic Authentication is Disabled

Then:

- Open: Configuration
- Enable: SCM Basic Auth Publishing Credentials
- Save the settings.

This allows Azure App Service to fetch the source code from Azure Repos.

Step 6: Configure Startup Command

Now configure the startup command for running the Streamlit application.

Go to:

- Configuration → General Settings

- Inside Startup Command, add:

- `streamlit run demo.py --server.port 8000 --server.address 0.0.0.0`

This command tells Azure App Service how to start the Streamlit application container.

Save the configuration.

Step 7: Configure Environment Variables

- Now configure the required application settings.

- Go to: Configuration → Application Settings

- Add the following environment variables.


Environment Variable 1
- Name: SCM_DO_BUILD_DURING_DEPLOYMENT and Value: 1

This tells Azure App Service to install dependencies during deployment.

Environment Variable 2
- Name: PORT and Value: 8080

This defines the application port.

Environment Variable 3

- Name: WEBSITES_PORT and Value: 8080

This tells Azure App Service which port the Streamlit application is running on. Save all application settings.

Step 8: Sync and Redeploy the Application

- Now return to: Deployment Center 
- Click: Sync

This triggers the deployment process again using the latest configurations.

Azure App Service will now:

- Fetch the source code from Azure Repos,
- create the runtime environment,
- install dependencies from requirements.txt,
and deploy the Streamlit application.


Step 9: Monitor Deployment Logs

To monitor deployment progress:

- Open: Logs
- View the deployment logs. The logs help verify: 

- dependency installation,
- virtual environment creation,
- deployment status,
and runtime issues.

Azure internally performs steps similar to manual deployment:

- creating environment,
- installing packages,
and starting the application container.


Step 10: Access the Streamlit Application

Once deployment is completed successfully:

- Go to: Overview
- Click: Browse

or open the application URL directly. The deployed Streamlit application will now be publicly accessible through Azure App Service.

Managing the Application

Azure App Service also allows:

- Start application
- Stop application
- Restart application
- Monitor logs
- Scale resources
- Redeploy automatically from Azure Repos

This makes deployment and management easier for production-oriented workflows.

