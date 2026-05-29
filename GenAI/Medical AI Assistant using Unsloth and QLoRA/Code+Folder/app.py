import streamlit as st
import torch
from unsloth import FastLanguageModel
from collections import deque
from transformers import BitsAndBytesConfig
# Configuration
max_seq_length = 2048
dtype = None
load_in_4bit = True

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = deque(maxlen=10)  # Buffer memory of last 10 messages
if "model" not in st.session_state:
    st.session_state.model = None
if "tokenizer" not in st.session_state:
    st.session_state.tokenizer = None

@st.cache_resource
def load_model():
    """Load the fine-tuned model and tokenizer"""
    try:
      bnb_config = BitsAndBytesConfig(
          load_in_4bit=True,
          llm_int8_enable_fp32_cpu_offload=True  # <-- offload heavy layers to CPU
      )


      model, tokenizer = FastLanguageModel.from_pretrained(
            model_name="/content/lora_model/lora_model",
            max_seq_length=max_seq_length,
            dtype=dtype,
            load_in_4bit=load_in_4bit,
            device_map="auto"
          )

      FastLanguageModel.for_inference(model)
      return model, tokenizer
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None, None

def format_conversation_history():
    """Format conversation history for context"""
    history = ""
    for msg in list(st.session_state.messages)[-6:]:  # Last 6 messages for context
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"
    return history

def generate_response(user_input, model, tokenizer):
    """Generate response using the fine-tuned model"""

    # Get conversation context
    context = format_conversation_history()

    # Create prompt with medical expert format
    prompt = f"""Below is an instruction that describes a task, paired with an input that provides further context.
Write a response that appropriately completes the request.

### Instruction:
You are a medical expert with advanced knowledge in clinical reasoning, diagnostics, and treatment planning.
Answer the following medical question with clarity, accuracy, and patient safety in mind.

### Previous Conversation:
{context}

### Question:
{user_input}

### Response:
"""

    # Tokenize input
    inputs = tokenizer(prompt +tokenizer.eos_token, return_tensors="pt").to("cuda")

    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
            max_new_tokens=2048,
            temperature=0.7,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode response
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract only the generated part (after "### Response:")
    if "### Response:" in response:
        response = response.split("### Response:")[-1].strip()

    return response

# Streamlit UI
st.title("🩺 Medical AI Chatbot")
st.markdown("*Powered by Fine-tuned Llama Model*")

# Load model if not already loaded
if st.session_state.model is None or st.session_state.tokenizer is None:
    with st.spinner("Loading model..."):
        model, tokenizer = load_model()
        if model and tokenizer:
            st.session_state.model = model
            st.session_state.tokenizer = tokenizer
            st.success("Model loaded successfully!")
        else:
            st.error("Failed to load model. Please check your model path.")
            st.stop()

# Display conversation history
st.subheader("Conversation")

# Create a container for messages
message_container = st.container()

with message_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Chat input
if user_input := st.chat_input("Ask your medical question..."):

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user"):
        st.write(user_input)

    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = generate_response(
                    user_input,
                    st.session_state.model,
                    st.session_state.tokenizer
                )
                st.write(response)

                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"Error generating response: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Sidebar with information
with st.sidebar:
    st.header("⚠️ Disclaimer")
    st.warning("""
    This AI chatbot is for demonstration purposes only.
    Always consult with qualified healthcare professionals
    for medical advice and treatment decisions.
    """)

    # Clear conversation button
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages.clear()
        st.rerun()

