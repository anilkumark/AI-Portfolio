from fastapi import BackgroundTasks
from fastapi import FastAPI
from source.personal_agents import PersonalAssistantOrchestrator
import time
from fastapi import FastAPI, Request, Header, HTTPException
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.signature import SignatureVerifier
from source.configurations import config

# FASTAPI app setup
app = FastAPI(title="Personal Assistant API", version="1.0.0")

assistant = PersonalAssistantOrchestrator()
SLACK_SIGNING_SECRET = config.SLACK_SIGNING_SECRET
SLACK_BOT_TOKEN = config.SLACK_BOT_TOKEN

slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)

async def handle_app_mention(event: dict):
    """
    This runs in the background: calls the LLM assistant and posts the reply.
    """
    try:
        user = event.get("user")
        channel = event.get("channel")
        text = event.get("text", "")
        ts = event.get("ts")  # Get timestamp for threading
        
        # Post initial acknowledgment message in thread
        await slack_client.chat_postMessage(
            channel=channel, 
            text="I am processing your request, please allow me sometime to respond.",
            thread_ts=ts
        )
        
        # Process the request
        result = await assistant.process_request(text)
        reply_text = result if isinstance(result, str) else result.get("response", str(result))
        
        # Post response in the same thread
        await slack_client.chat_postMessage(
            channel=channel, 
            text=reply_text,
            thread_ts=ts
        )
    except Exception as e:
        print(f"Error handling app_mention: {e}")

@app.post("/slack/events")
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
):
    # Verify timestamp is recent
    if x_slack_request_timestamp is None or abs(time.time() - int(x_slack_request_timestamp)) > 60 * 5:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
    body_bytes = await request.body()
    # Verify signature
    if not verifier.is_valid(body=body_bytes, timestamp=x_slack_request_timestamp, signature=x_slack_signature):
        raise HTTPException(status_code=400, detail="Invalid Slack signature")
    payload = await request.json()
    # URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    # Handle event callbacks
    event = payload.get("event", {})
    if event.get("type") == "app_mention":
        # Schedule background task; do NOT await assistant.process_request here
        background_tasks.add_task(handle_app_mention, event)
    # Always return 200 OK immediately
    return {"ok": True}