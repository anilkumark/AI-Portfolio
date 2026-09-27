"""Streamlit chat UI for the refund multi-agent system."""

import logging
import os
import time
import uuid

import requests
import streamlit as st

from refund_system.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("refund_system.ui")

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
CHAT_URL = f"{API_BASE}/chat"
STATUS_URL = f"{API_BASE}/status"

st.set_page_config(page_title="Refund Assistant", page_icon="💬")
st.title("Refund Assistant")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "waiting_for_approval" not in st.session_state:
    st.session_state.waiting_for_approval = False

if "customer_id" not in st.session_state:
    st.subheader("Please sign in")
    entered_id = st.text_input("Customer ID")
    if st.button("Continue") and entered_id:
        st.session_state.customer_id = entered_id
        st.rerun()
    st.stop()


def send_message(text: str) -> None:
    logger.info("UI calling API /chat | thread_id=%s", st.session_state.thread_id)
    response = requests.post(
        CHAT_URL,
        json={
            "thread_id": st.session_state.thread_id,
            "customer_id": st.session_state.customer_id,
            "message": text,
        },
    )
    data = response.json()
    logger.info("UI received reply from API | thread_id=%s", st.session_state.thread_id)
    st.session_state.messages.append({"role": "assistant", "content": data["reply"]})
    st.session_state.waiting_for_approval = data["interrupted"]


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

    with st.spinner("Thinking..."):
        send_message(prompt)

    st.rerun()

if st.session_state.waiting_for_approval:
    status_response = requests.get(f"{STATUS_URL}/{st.session_state.thread_id}")
    status_data = status_response.json()

    if status_data is not None and status_data["status"] != "pending":
        logger.info(
            "UI detected resolved approval | thread_id=%s | status=%s",
            st.session_state.thread_id,
            status_data["status"],
        )
        st.session_state.waiting_for_approval = False
        with st.spinner("Getting the outcome..."):
            send_message("What's the status of my refund request?")
        st.rerun()
    else:
        with st.chat_message("assistant"):
            st.info("⏳ Waiting for manager approval — this page updates automatically.")
        time.sleep(5)
        st.rerun()
