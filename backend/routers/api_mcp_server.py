import logging
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from database import get_es_client

logger = logging.getLogger(__name__)
router = APIRouter()

server = Server("instasearch-api-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_post_trends",
            description="取得指定欄位（目前固定為 datetime 按月分群）的發文數量趨勢",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_post_trends":
        es = get_es_client()
        agg_query = {
            "aggs": {
                "posts_over_time": {
                    "date_histogram": {
                        "field": "datetime",
                        "calendar_interval": "month"
                    }
                }
            },
            "size": 0
        }
        
        try:
            res = es.search(index="ig_data", body=agg_query)
            buckets = res['aggregations']['posts_over_time']['buckets']
            
            import json
            from datetime import datetime
            data = [{"date": datetime.fromtimestamp(b['key']/1000).strftime('%Y-%m'), "count": b['doc_count']} for b in buckets]
            return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting trends: {str(e)}")]

    raise ValueError(f"Unknown tool: {name}")

sse = SseServerTransport("/api-mcp/messages")

async def sse_app(scope, receive, send):
    async with sse.connect_sse(scope, receive, send) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )

async def messages_app(scope, receive, send):
    await sse.handle_post_message(scope, receive, send)

router.mount("/sse", sse_app)
router.mount("/messages", messages_app)
