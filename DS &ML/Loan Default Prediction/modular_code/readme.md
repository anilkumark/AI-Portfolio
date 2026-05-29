# Overview
Loan default prediction is a critical application in the financial industry, where lenders and institutions aim to assess the risk associated with providing loans to individuals or businesses. The goal is to identify potential borrowers more likely to default on their loans, allowing lenders to make informed decisions and mitigate financial risks.

In the context of loan default prediction, machine learning models have shown promising results in accurately predicting whether a borrower will default on a loan. These models leverage historical data, such as past loan performance, financial history, employment details, and other relevant factors, to predict the likelihood of future loan defaults.

However, as machine learning models become increasingly complex, a significant challenge arises the lack of transparency. Many modern machine learning algorithms, such as deep neural networks, can be seen as "black boxes." While they may produce accurate predictions, how they arrive at those predictions is often unclear. This opacity raises concerns for various stakeholders involved in the loan lending process:

Data Scientists: Data scientists who develop and deploy these models need to understand their inner workings for debugging, improvement, and model selection. They require insights into feature importance and decision processes to ensure models are reliable and accurate.

Stakeholders: Business stakeholders, such as loan officers and management teams, need to trust and comprehend the model's predictions to make well-informed lending decisions. Clear explanations are essential for building trust and facilitating collaboration between data scientists and business units.

Regulators: Regulatory bodies and compliance officers demand transparency in lending practices. They require models to be explainable and auditable to ensure fairness, ethical considerations, and compliance with regulations like anti-discrimination laws.



# Execution Instructions

# Python version 3.10.4

To create a virtual environment and install requirements in Python 3.10.4 on different operating systems, follow the instructions below:

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

`python3 -m venv myenv`

Activate the virtual environment:

`source myenv/bin/activate`

Install the project requirements using pip:

`pip install -r requirements.txt`

These instructions assume you have Python 3.10.4 installed and added to your system's PATH variable.


## Execution Instructions if Multiple Python Versions Installed


If you have multiple Python versions installed on your system , you can use the Python Launcher to create a virtual environment with Python 3.10.4, you can specify the version using the -p or --python flag. Follow the instructions below:

### For Windows:

Open the Command Prompt by pressing Win + R, typing "cmd", and pressing Enter.

Change the directory to the desired location for your project:

`cd C:\path\to\project`

Create a new virtual environment using the Python Launcher:

`py -3.10 -m venv myenv`

Note: Replace myenv with your desired virtual environment name.

Activate the virtual environment:

`myenv\Scripts\activate`

Install the project requirements using pip:

`pip install -r requirements.txt`


For Linux/Mac:

Open a terminal.

Change the directory to the desired location for your project:

`cd /path/to/project`

Create a new virtual environment using the Python Launcher:

`python3.10 -m venv myenv`
Note: Replace myenv with your desired virtual environment name.

Activate the virtual environment:

`source myenv/bin/activate`
Install the project requirements using pip:

`pip install -r requirements.txt`


By specifying the version using py -3.10 or python3.10, you can ensure that the virtual environment is created using Python 3.10.4 specifically, even if you have other Python versions installed.







```
├─ engine.py
├─ Input
│  ├─ CleanedData.xlsx
│  ├─ Cleaned_SampledData.xlsx
│  ├─ Credit_Risk_Dataset.xlsx
├─ Notebooks
│  ├─ 1. Data prep and ML.ipynb
│  ├─ 2. Explainable AI.ipynb
│  └─ Source
|
├─ Output
├─ readme.md
├─ requirements.txt
└─ Source
   ├─ eda.py
   ├─ machine_learning.py
   ├─ setup.py
```





