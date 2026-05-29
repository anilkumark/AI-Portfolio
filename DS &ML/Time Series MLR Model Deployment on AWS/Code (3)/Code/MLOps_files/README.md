# Code Implementation


1. Running the codes locally: Python 3.7
    - Create a virtual environment: In the terminal or command prompt, use the following command to create a new virtual environment:

        - For Windows:
            `py -3.7 -m venv venv`

        - For macOS and Linux:
            `python3 -m venv venv`
        This command creates a new virtual environment named "venv" in the current directory.

    - Activate the virtual environment:

        - For Windows (Command Prompt):
            `venv\Scripts\activate.bat`


        - For macOS and Linux (Terminal) :
            `source venv/bin/activate`
    
    Once the virtual environment is activated, you should see the environment name (e.g., (venv)) in the terminal or command prompt.

    - Install project requirements: With the virtual environment active, you can now install the required packages for your project. Typically, the required packages are listed in a requirements.txt file. Make sure you have the requirements.txt file for your project.

    - To install the requirements, use the following command:
        `pip install -r requirements.txt`

    - Run Jupyter Notebooks
    - Run docker file:
        - Install Docker on your system
        - Open cmd with Administrative rights
        - Change Directory to the directory where dockerfile is present
        - Run the commands:
            - `docker  build` - It should take around 15 -20 minutes if running for the first time.
            