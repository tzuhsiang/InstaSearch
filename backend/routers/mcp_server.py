import logging
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from database import get_es_client

logger = logging.getLogger(__name__)
router = APIRouter()

server = Server("instasearch-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_instagram",
            description="Search Instagram posts for a query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "search_instagram":
        query = arguments.get("query")
        if not query:
            return [types.TextContent(type="text", text="Error: No query provided")]
            
        es = get_es_client()
        try:
            res = es.search(
                index="ig_data",
                body={
                    "query": {"match": {"content": query}},
                    "size": 5
                }
            )
            hits = res.get("hits", {}).get("hits", [])
            if not hits:
                 return [types.TextContent(type="text", text="No results found.")]
            
            result_text = "Found Posts:\n"
            for hit in hits:
                s = hit["_source"]
                result_text += f"- [{s.get('datetime', '?')}] {s.get('content', '')[:100]}...\n"
                
            return [types.TextContent(type="text", text=result_text)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error searching: {str(e)}")]

    raise ValueError(f"Unknown tool: {name}")

# /mcp/messages is the endpoint within the FastAP APIRouter, but the router is prefixed with /mcp in main.py
# So the full path will be /mcp/messages
sse = SseServerTransport("/mcp/messages")

@router.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(
            streams.read_stream,
            streams.write_stream,
            server.create_initialization_options()
        )

@router.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)
