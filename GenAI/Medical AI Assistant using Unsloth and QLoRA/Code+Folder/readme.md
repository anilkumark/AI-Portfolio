
# Medical LLaMA Fine-tuning Project

This  demonstrates fine-tuning a LLaMA model for medical question answering using LoRA (Low-Rank Adaptation) and QLoRA techniques.

## Project Structure
```
medical-fine-tuning
├─ app.py                           # Streamlit chatbot application
├─ lora_model.zip                   # Compressed fine-tuned model
├─ medical_llama_finetuning.ipynb   # Main training notebook
├─ readme.md                        # This file
└─ requirements.txt                 # Python dependencies
```

## Setup Instructions

### Option 1: Google Colab (Recommended for Beginners)



2. **Install Python 3.12** (if needed):
   ```bash
   # Check current Python version
   !python --version
   
   # If not 3.12, install it
   !apt update
   !apt install -y python3.12 python3.12-pip python3.12-venv
   !update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
   ```

3. **Install Requirements**:
   ```bash
   !pip install -r requirements.txt
   ```



#### Step 3: Run the Notebook
1. **Open** `medical_llama_finetuning.ipynb`
2. **Run cells sequentially** from top to bottom
3. **Monitor GPU usage**: Runtime → Manage sessions

### Option 2: Local GPU Setup

#### Prerequisites
- NVIDIA GPU with at least 8GB VRAM (RTX 3080/4080 recommended)
- CUDA 11.8+ installed
- Python 3.12

#### Step 1: Environment Setup

**For Linux/macOS:**
```bash
# Create virtual environment
python3.12 -m venv medical_env
source medical_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify CUDA installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count()}')"
```

**For Windows:**
```cmd
# Create virtual environment
python -m venv medical_env

# Activate virtual environment
medical_env\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify CUDA installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count()}')"
```


#### Step 2: Launch Jupyter
```bash
# Install Jupyter if not already installed
pip install jupyter

# Launch Jupyter Notebook
jupyter notebook

# Or use JupyterLab
pip install jupyterlab
jupyter lab
```

#### Step 3: Memory Management
If you encounter memory issues:
```python
# Add at the beginning of your notebook
import torch
torch.cuda.empty_cache()

# Monitor GPU memory
!nvidia-smi
```

### Option 3: Cloud Instance (AWS EC2, GCP, etc.)

#### AWS EC2 Setup
1. **Launch EC2 Instance**:
   - AMI: Deep Learning AMI (Ubuntu) - includes CUDA/cuDNN
   - Instance Type: `g4dn.xlarge` or `p3.2xlarge`
   - Storage: At least 50GB

2. **Connect and Setup**:
   ```bash
   # Connect via SSH
   ssh -i your-key.pem ubuntu@your-instance-ip
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.12
   sudo apt install -y python3.12 python3.12-pip python3.12-venv
   
   # Create virtual environment
   python3.12 -m venv medical_env
   source medical_env/bin/activate
   
   # Clone/upload your project
   git clone <your-repo> # or upload files
   cd medical-fine-tuning
   
   # Install requirements
   pip install -r requirements.txt
   ```

3. **Create a python script of all codes and run**

## Running the Streamlit App

### Local Deployment

**For Linux/macOS:**
```bash
# Activate environment
source medical_env/bin/activate

# Run Streamlit app
streamlit run app.py

# Access at http://localhost:8501
```

**For Windows:**
```cmd
# Activate environment
medical_env\Scripts\activate

# Run Streamlit app
streamlit run app.py

# Access at http://localhost:8501
```

### Colab Deployment
```python
# In Colab notebook
!streamlit run app.py --server.port 8501 &>/dev/null&

# Use ngrok for public access
from pyngrok import ngrok
public_url = ngrok.connect(8501)
print("Access the app here:", public_url)
```
