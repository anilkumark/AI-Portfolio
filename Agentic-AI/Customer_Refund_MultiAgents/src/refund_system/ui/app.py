"""Streamlit chat UI for the refund multi-agent system."""

import uuid

import requests
import streamlit as st

import logging

from refund_system.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("refund_system.ui")


import os

API_URL = os.environ.get("API_URL", "http://localhost:8000/chat")


st.set_page_config(page_title="Refund Assistant", page_icon="💬")
st.title("Refund Assistant")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "customer_id" not in st.session_state:
    st.subheader("Please sign in")
    entered_id = st.text_input("Customer ID")
    if st.button("Continue") and entered_id:
        st.session_state.customer_id = entered_id
        st.rerun()
    st.stop()


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("How can I help with your refund?"):
    logger.info(
        "UI received user message | thread_id=%s | message=%r",
        st.session_state.thread_id,
        prompt,
    )
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    logger.info("UI calling API /chat | thread_id=%s", st.session_state.thread_id)
    response = requests.post(
        API_URL,
        json={
            "thread_id": st.session_state.thread_id,
            "customer_id": st.session_state.customer_id,
            "message": prompt,
        },
    )

    reply = response.json()["reply"]
    logger.info("UI received reply from API | thread_id=%s", st.session_state.thread_id)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
