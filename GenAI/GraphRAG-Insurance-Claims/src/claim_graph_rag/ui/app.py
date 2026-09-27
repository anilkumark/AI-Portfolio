"""Streamlit chat UI for the claim analysis Graph RAG system."""

import requests
import streamlit as st

API_URL = "http://localhost:8000/ask"

st.set_page_config(page_title="Claim Analysis Assistant", page_icon="📋")
st.title("Claim Analysis Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Ask about a claim or policy..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("Thinking..."):
        response = requests.post(API_URL, json={"question": prompt})
        data = response.json()

    answer = data["answer"]
    if not data["valid"]:
        answer += "\n\n⚠️ This answer failed validation and may contain inaccuracies."

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
