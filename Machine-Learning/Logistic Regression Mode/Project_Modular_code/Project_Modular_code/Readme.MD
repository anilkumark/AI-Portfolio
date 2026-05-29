## **Project Overview**

Customer retention is a critical challenge for subscription-based digital platforms, especially in the highly competitive video streaming industry. Acquiring new customers is significantly more expensive than retaining existing ones, making early identification of potential churners essential for business sustainability and growth.

In this project, we focus on predicting customer churn for a video streaming service provider. Customer churn refers to users who decide not to renew their subscription after the current plan period ends. Accurately predicting churn allows companies to proactively design retention strategies, offer personalized incentives, and optimize customer engagement efforts. The dataset used in this project contains approximately 2,000 customer records with 16 features, including demographic details, subscription behavior, and service usage patterns. The objective is to build a robust and interpretable classification model that determines whether a customer is likely to churn or continue their subscription.

Throughout this project, we emphasize not only model performance but also interpretability, data imbalance handling, and feature selection, ensuring that the results can be confidently used for real-world business decision-making.

### Steps for running the notebook locally

The Python 3.8 version is supported for the execution of this project.
1. Running the codes locally: Python 3.8
    - Create a virtual environment: In the terminal or command prompt, use the following command to create a new virtual environment:

        - For Windows:
            `py -3.8 -m venv env`

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

* Run engine.py with the command 'python3 engine.py'.

