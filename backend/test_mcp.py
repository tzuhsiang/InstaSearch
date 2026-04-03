import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from contextlib import AsyncExitStack

async def run():
    async with AsyncExitStack() as stack:
        try:
            streams = await stack.enter_async_context(sse_client("http://127.0.0.1:8000/mcp/sse"))
            session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
            resp = await session.list_tools()
            print("instagram tools:", [t.name for t in resp.tools])
        except Exception as e:
            print("instagram ERROR:", e)

        try:
            streams2 = await stack.enter_async_context(sse_client("http://127.0.0.1:8000/api-mcp/sse"))
            session2 = await stack.enter_async_context(ClientSession(streams2[0], streams2[1]))
            await session2.initialize()
            resp2 = await session2.list_tools()
            print("system_api tools:", [t.name for t in resp2.tools])
        except Exception as e:
            print("system_api ERROR:", e)

asyncio.run(run())
