import asyncio
from uuid import uuid4

import httpx

from a2a.client import A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    TextPart,
)


async def main():
    async with httpx.AsyncClient() as httpx_client:
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, "http://localhost:8080"
        )

        message = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[
                Part(
                    root=TextPart(
                        text="John Doe|patient reported neck pain after being rear-ended|2026-01-15"
                    )
                )
            ],
        )

        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=message),
        )

        response = await client.send_message(request)
        print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
