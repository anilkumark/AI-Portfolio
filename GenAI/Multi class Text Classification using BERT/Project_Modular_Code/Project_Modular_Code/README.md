### AG News Text Classification with BERT ###

This repository covers the code for performing text classification on the AG News dataset using state-of-the-art transformer model BERT.
AG News (AG’s News Corpus) is a sub dataset of AG's corpus of news articles 
constructed by assembling titles and description fields of articles, from the 4 largest classes (“World”, “Sports”, “Business”, “Sci/Tech”)
of AG’s Corpus.
BERT is a state-of-the-art transformer model use to perform complex NLP tasks like NLU, NLG, Sentiment Analysis,
Text Classification...., and it gives very high performance metrics with respect to these, sometimes even surpassing human capabilities.

Below are the steps to be followed:
### Python version 3.8.10

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


   
2. The entire repository is modularised in to individual sections which performs specific task.
   First, go to src folder.
   Under src, there are 2 primary packages:
   a> ML_Pipeline:
   This contains individual modules with different function declarations to perform specific Machine Learning task.
   b> engine.py:
   This is the heart of the project, as all the function calls are done here.
   
3. Run/Debug the engine.py file and all the steps will be automatically taken care as per the logic.

4. All input datasets are stored in the input folder.

5. All predictions and models are stored in the output folder.



