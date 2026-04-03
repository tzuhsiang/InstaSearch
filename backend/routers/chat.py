import asyncio
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent import build_graph

logger = logging.getLogger(__name__)

router = APIRouter()

# Global graph instance set during main's lifespan
router.agent_graph = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

@router.get("/config")
def get_config():
    from config import DEFAULT_SUGGESTIONS
    return {"default_suggestions": DEFAULT_SUGGESTIONS}

@router.post("/chat")
async def chat(req: ChatRequest):
    async def generate():
        if router.agent_graph is None:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Agent not initialized'})}\n\n"
            return

        messages = []
        for msg in req.history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        messages.append(HumanMessage(content=req.message))

        try:
            async for event in router.agent_graph.astream_events(
                {"messages": messages}, 
                version="v2"
            ):
                kind = event["event"]
                name = event["name"]
                
                if kind == "on_chain_start":
                    if name == "supervisor":
                        yield f"data: {json.dumps({'type': 'step', 'content': '👀 指揮官正在評估意圖...'})}\n\n"
                    elif name == "retriever":
                        yield f"data: {json.dumps({'type': 'step', 'content': '🔍 準備抓取社群資料...'})}\n\n"
                    elif name == "reporter":
                        yield f"data: {json.dumps({'type': 'step', 'content': '✍️ 正在撰寫美食報告...'})}\n\n"
                    elif name == "info_agent":
                        yield f"data: {json.dumps({'type': 'step', 'content': '🤖 系統專員正在解答...'})}\n\n"

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    
                    if node_name in ["reporter", "info_agent"]:
                        if hasattr(chunk, "content") and chunk.content and isinstance(chunk.content, str):
                            yield f"data: {json.dumps({'type': 'stream_text', 'content': chunk.content})}\n\n"
                            
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc in chunk.tool_call_chunks:
                            tool_name = tc.get("name")
                            if tool_name:
                                payload = {'type': 'reasoning', 'content': f'🔧 啟動工具: {tool_name}'}
                                yield f"data: {json.dumps(payload)}\n\n"
                
                elif kind == "on_tool_start" and name == "update_search_ui":
                    args = event["data"].get("input", {})
                    payload = {
                        "type": "ui_command",
                        "command": "update_search",
                        "params": args
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    data = event["data"].get("output")
                    if data:
                        try:
                            # 嘗試計算回傳的筆數
                            data_str = data.content if hasattr(data, "content") else str(data)
                            try:
                                parsed = json.loads(data_str)
                                count = parsed.get("total", len(parsed.get("data", [])) if isinstance(parsed, dict) else len(parsed))
                                yield f"data: {json.dumps({'type': 'reasoning', 'content': f'📦 工具 {tool_name} 執行完成，獲得: {count} 筆資料'})}\n\n"
                            except Exception:
                                # 非 JSON 或字串，直接略過筆數計算
                                yield f"data: {json.dumps({'type': 'reasoning', 'content': f'✅ 工具 {tool_name} 執行完畢'})}\n\n"
                        except Exception:
                            pass
                
                elif kind == "on_chain_end" and name == "suggester":
                    output = event["data"].get("output")
                    if output and "messages" in output:
                        try:
                            for msg in output["messages"]:
                                if hasattr(msg, "additional_kwargs") and msg.additional_kwargs.get("is_suggestions"):
                                    parsed_final = json.loads(msg.content)
                                    suggestions = parsed_final.get("suggestions", [])
                                    if suggestions:
                                        yield f"data: {json.dumps({'type': 'suggestions', 'data': suggestions})}\n\n"
                                    break
                        except Exception as e:
                            logger.error(f"Failed to parse suggestions output: {e}")

        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
