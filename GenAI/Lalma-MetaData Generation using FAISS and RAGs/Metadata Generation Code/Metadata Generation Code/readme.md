# Setup AWS EC2 for Code Execution

## Launch an AWS EC2 Instance

1. **Choose Image:** Ubuntu Pro Linux
2. **Architecture:** 64-bit (x86)
3. **Instance Type:** g4dn.2xlarge
4. **Storage:** 64 GB
5. **Generate a pem key** and save it in a directory
6. **Network** to be decided as per system requirements

## Access EC2 Instance

1. Locate the pem key in your system and revoke access except admin.
2. Open a command prompt as an administrator and set the working directory where the pem key is stored.
3. Go to the EC2 console and connect to the recently created EC2 instance.
4. Use SSH to connect to your EC2 instance. You will need the private key associated with your instance.

```bash
ssh -i your-key.pem ec2-user@your-ec2-instance-public-ip
```

Paste this command in the command prompt to establish a connection to EC2.

Follow these instructions to set up the project on a Linux system with an NVIDIA GPU.

## GPU Setup

* **Purge Existing NVIDIA Drivers:**
   * `sudo apt-get purge nvidia*`
   * *Removes any existing NVIDIA drivers to avoid conflicts.*

* **Add NVIDIA Graphics Driver Repository:**
   * `sudo add-apt-repository ppa:graphics-drivers/ppa`
   * `sudo apt update`
   * *Adds the official NVIDIA PPA for the latest drivers.*

* **Install Specific NVIDIA Driver:**
   * `sudo apt install nvidia-driver-535`
   * *Replace 535 with the latest driver version number from the NVIDIA website. Reboot system after installation.*

* **Reboot System:**
   * `sudo reboot`
   * *Reboots your system to apply changes.*

* **Verify Installation:**
   * `nvidia-smi`
   * *Checks and displays details about the GPU and the installed driver version.*

* **Install CUDA Toolkit:**
   * `sudo apt install nvidia-cuda-toolkit`
   * `nvcc --version`
   * *Installs CUDA Toolkit for GPU acceleration and verifies the installation.*

## Project Setup

* **Update System Packages and Add Python Repository:**
   * `sudo apt update`
   * `sudo apt install software-properties-common`
   * `sudo add-apt-repository ppa:deadsnakes/ppa`
   * `sudo apt install python3`
   * `sudo apt install python3-pip`
   * *Ensures system packages are up to date and installs Python 3.*

## Python Environment Setup

* **Install Virtual Environment Tools:**
   * `pip install virtualenv`
   * `sudo apt install python3-venv`

* **Create and Activate Virtual Environment:**
   * `python3 -m venv venv`
   * `source venv/bin/activate`
   * `pip install "pip<24.1"`

* **Transfer Your Python Script from Local Machine to EC2**
   * Open another command prompt with admin access and set the working directory where the pem key is stored.
   * Use the `scp` command to transfer your Python script from your local machine to the EC2 instance.

```bash
scp -i your-key.pem your_code_folder_location -r ec2-user@your-ec2-instance-public-ip:/path/to/ec2/location
```

* **Install Required Packages:**
   * `pip install -r requirements.txt`
   * *Install packages from requirements file (note: pip version <24.1 is required for textract compatibility)*
   * `pip install autoawq`
   * *Install autoawq separately after requirements*

### Common textract Installation Error

If you encounter the following error when installing requirements.txt, it indicates you need to downgrade pip:

```
WARNING: Ignoring version 1.6.5 of textract since it has invalid metadata: 
Requested textract from https://files.pythonhosted.org/packages/...textract-1.6.5-py3-none-any.whl 
has invalid metadata: .* suffix can only be used with == or != operators 
extract-msg (<=0.29.*) ~~~~~~~^
Please use pip<24.1 if you need to use this version.
```

This error occurs because newer pip versions have stricter metadata validation. Use `pip install "pip<24.1"` to resolve this issue.

## Code Execution

Activate the virtual environment and run the script

* `source venv/bin/activate`
* `python3 main.py`

To run the streamlit UI

* `source venv/bin/activate`
* `streamlit run streamlit_main.py`


*** Fix: Apache Tika / Textract Error in EC2 (LLM Project)  ***

Issue

While running the Streamlit application, the following error may occur:

Tika startup log message not received after 3 tries.
Failed to receive startup confirmation from startServer.

This happens because Apache Tika requires Java, which is not installed by default on a fresh EC2 instance.

Solution

Step 1: Install Java (OpenJDK)

Run the following commands on your EC2 instance:

 - sudo apt update
- sudo apt install -y openjdk-11-jdk

Step 2: Verify Java Installation
- java -version

Expected Output:

openjdk version "11.x.x"


Step 3: Restart the Application

Stop the currently running Streamlit app:

- Ctrl + C

Then restart:

- streamlit run streamlit_main.py --server.port 8501 --server.address 0.0.0.0

Why This Fix Works
textract internally uses Apache Tika
Apache Tika requires a Java Runtime Environment (JRE)
Without Java, Tika fails to initialize, causing document parsing errors

*** Notes ***

You may see warnings like:

LangChainDeprecationWarning

These are non-breaking warnings and can be ignored for now.

*** Optional Fix (If Issue Persists) **8 

If Tika still fails to start, reinstall it:

- pip uninstall tika -y
- pip install tika

## Files

* **utils.py:** contains all the functions required for creating vector db, Q/A, model and pipeline creation
* **main.py:** main code to execute the pipeline with questions as user input
* **configs.py:** variable/configuration storage
* **streamlit_main.py:** streamlit ui code to upload a file and get answer to a single question
* **sample_files/preprocessing.py:** sample test file for execution (update them as per your requirements)
* **requirements.txt:** all the required libraries with respective versions

## Notes

* Always check for the latest versions of software and dependencies for compatibility.
* Replace `535` with the actual latest driver version from the NVIDIA website.
* It's important to verify the installation of each component before proceeding to the next step.
* **Important:** Use pip version <24.1 to avoid textract installation issues. The newer pip versions have stricter metadata validation that causes textract 1.6.5 to fail with invalid dependency specification errors.
* Install autoawq separately after installing requirements.txt to ensure proper dependency resolution.


## Local Execution
Python 3.10 must be installed.
Ensure you have access to the required datasets and connection strings for databases.

### Virtual Environment Setup Instructions

#### For Mac and Linux:
Open a terminal and navigate to the project directory:

`cd /path/to/metadata-gen`



##### Create a virtual environment using venv:

`python3 -m venv venv`


Activate the virtual environment:


`source venv/bin/activate`

Install the required dependencies from the requirements.txt file:


`pip install -r requirements.txt`

#### For Windows:
Open a command prompt and navigate to the project directory:

`cd \path\to\SQLGenPro`

Create a virtual environment using venv:

`python -m venv venv`


Activate the virtual environment:

`.\venv\Scripts\activate`

Install the required dependencies from the requirements.txt file:


`pip install -r requirements.txt`



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

### Set Java Path
`set PATH=C:\Program Files\Java\jdk-24\bin;%PATH%`