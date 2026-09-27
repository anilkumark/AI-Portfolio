"""Entry point that runs uvicorn on a SelectorEventLoop, required by
psycopg's async driver (the checkpointer MCP's async-only tools need).
uvicorn.run() resets the policy to Proactor internally on Windows, so this
bypasses it and drives the server loop manually instead."""

import asyncio
import sys

import uvicorn

from wealth_agent.api.main import app

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = uvicorn.Config(app, host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
