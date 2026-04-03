import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from pydantic import BaseModel, Field, create_model
from langchain_core.tools import StructuredTool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_DEPLOYMENT_NAME,
    MCP_SERVERS_DICT,
)

logger = logging.getLogger("agent")

# Global MCP State
_mcp_stack = AsyncExitStack()
_mcp_tools: List[StructuredTool] = []

async def init_mcp_client():
    global _mcp_tools, _mcp_stack
    _mcp_stack = AsyncExitStack()
    _mcp_tools = []
    
    for server_name, url in MCP_SERVERS_DICT.items():
        try:
            streams = await _mcp_stack.enter_async_context(sse_client(url))
            session = await _mcp_stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
            
            tool_resp = await session.list_tools()
            
            for m_tool in tool_resp.tools:
                original_name = m_tool.name
                m_tool.name = f"{server_name}_{original_name}"
                _mcp_tools.append(_create_langchain_tool(m_tool, session, original_name))
                
            logger.info(f"✅ 掛載成功: {server_name} 於 {url}")
        except Exception as e:
            logger.error(f"❌ 掛載失敗: {server_name} 於 {url} (連線錯誤: {e})")
            # Raise exception so the background retry loop catches it and retries
            raise RuntimeError(f"Failed to load MCP server {server_name}") from e
            
    logger.info(f"🎉 啟動完成！總共成功載入 {len(_mcp_tools)} 支 MCP 工具。")

async def close_mcp_client():
    global _mcp_stack
    await _mcp_stack.aclose()

def _create_langchain_tool(m_tool, session, original_name: str) -> StructuredTool:
    """Dynamically converts an MCP Tool to a LangChain StructuredTool."""
    async def _arun(**kwargs) -> str:
        try:
            res = await session.call_tool(original_name, arguments=kwargs)
            if res.isError:
                return f"Error from Tool: {res.content}"
            # Extract text from content
            texts = []
            for c in res.content:
                if hasattr(c, "text"):
                    texts.append(c.text)
                elif isinstance(c, dict) and "text" in c:
                    texts.append(c["text"])
                else:
                    texts.append(str(c))
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error: {e}"

    # Build Pydantic model for args_schema based on inputSchema
    fields = {}
    props = m_tool.inputSchema.get("properties", {})
    required = m_tool.inputSchema.get("required", [])
    
    for k, v in props.items():
        v_type = v.get("type")
        t = str
        if v_type == "integer": t = int
        elif v_type == "boolean": t = bool
        elif v_type == "number": t = float
        elif v_type == "array": t = list
        elif v_type == "object": t = dict
        
        desc = v.get("description", "")
        if k in required:
            fields[k] = (t, Field(..., description=desc))
        else:
            fields[k] = (Optional[t], Field(None, description=desc))
            
    # Always ensure a valid model, even if no args
    args_schema = create_model(f"{m_tool.name}Schema", **fields)
    
    return StructuredTool(
        name=m_tool.name,
        description=m_tool.description or "No description",
        args_schema=args_schema,
        func=lambda **kwargs: "Synchronous execution not supported",
        coroutine=_arun
    )


from typing import Literal

class SuggestionResponse(BaseModel):
    suggestions: List[str] = Field(
        description="2到3個推薦後續提問。請使用陳述句或祈使句指令（例如：'查詢信義區的義大利麵'），絕對不要使用問句形式。"
    )

class RouterOutput(BaseModel):
    next_node: Literal["retriever", "reporter", "info_agent", "FINISH"] = Field(
        description="決定下一步：需要查資料選 retriever；需結構化報告選 reporter；單純問系統功能或閒聊選 info_agent；任務結束選 FINISH"
    )

def build_graph() -> StateGraph:
    llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_DEPLOYMENT_NAME,
        temperature=0,
        streaming=True
    )

    async def run_supervisor(state: MessagesState):
        messages = state["messages"]
        sys_prompt = SystemMessage(content=(
            "你是 Instagram 食記分析的主管 (Supervisor)。"
            "負責決定下一個要執行的部門。你看不到實際食記資料，只能規劃。\n"
            "如果有需要深入查詢 IG 貼文、尋找餐廳或分析發文趨勢，請交由 'retriever'。\n"
            "如果資料已經查夠了（已產生 ToolMessage），或是使用者僅要求純粹撰寫報告，請交由 'reporter'。\n"
            "如果使用者單純閒聊、打招呼或是詢問『系統有哪些功能』，請派給 'info_agent'。\n"
            "直接判斷下一個節點，請勿回答其他內容。"
        ))
        msg_list = [sys_prompt] + messages
        router_llm = llm.with_structured_output(RouterOutput)
        response = await router_llm.ainvoke(msg_list)
        return {"messages": [AIMessage(content="", additional_kwargs={"next_node": response.next_node})]}

    async def run_info_agent(state: MessagesState):
        messages = state["messages"]
        valid_messages = [m for m in messages if not m.additional_kwargs.get("next_node")]
        tools_list = "\n".join([f"- {t.name}: {t.description}" for t in _mcp_tools])
        sys_prompt = SystemMessage(content=(
            "你是系統資訊回覆專員。你的任務是熱情地回覆使用者的閒聊，或解說系統具備的能力。\n"
            f"系統目前掛載了以下 MCP Tools 可以用來查詢食記與發文趨勢：\n{tools_list}\n"
            "請留意！你並無法實際執行這些工具。你只能向使用者解說功能。"
        ))
        msg_list = [sys_prompt] + valid_messages
        response = await llm.ainvoke(msg_list)
        return {"messages": [response]}

    async def run_retriever(state: MessagesState):
        messages = state["messages"]
        valid_messages = [m for m in messages if not m.additional_kwargs.get("next_node")]
        
        tools_list = "\n".join([f"- {t.name}: {t.description}" for t in _mcp_tools])
        sys_prompt = SystemMessage(content=(
            "你是資料收集專員 (Retriever)。請依照使用者需求呼叫相應的工具取得 IG 貼文與美食資訊。\n"
            f"可用的 MCP Tools 如下：\n{tools_list}\n"
            "如果已經呼叫過工具且無需再查，或是使用者未提供足夠搜尋字眼，請回答準備寫報告。"
        ))
        
        msg_list = [sys_prompt] + valid_messages
        model_with_tools = llm.bind_tools(_mcp_tools)
        response = await model_with_tools.ainvoke(msg_list)
        return {"messages": [response]}

    async def run_reporter(state: MessagesState):
        messages = state["messages"]
        valid_messages = [m for m in messages if not m.additional_kwargs.get("next_node")]
        sys_prompt = SystemMessage(content=(
            "你是資深 IG 食記編輯員 (Reporter)。你手上沒有查詢工具，任務是從對話歷史的 JSON 結果擷取資訊，並寫成極具質感的 Markdown 報告。\n"
            "報告內請提供圖文並茂的格式，摘要店名、餐點與評價。請直接輸出一篇專業的 Markdown 食評報告或分析趨勢。"
        ))
        msg_list = [sys_prompt] + valid_messages
        response = await llm.ainvoke(msg_list)
        return {"messages": [response]}

    async def run_suggester(state: MessagesState):
        messages = state["messages"]
        valid_messages = [m for m in messages if not m.additional_kwargs.get("next_node")]
        sys_prompt = SystemMessage(content=(
            "你是推薦引導專員。請根據上下文，提供 2 到 3 個使用者可以進行的「下一步指令」。\n"
            "這些推薦會作為按鈕文字供使用者點擊，請使用陳述句或動作指令（例如：「查詢最近拉麵店的排行」）。\n"
            "嚴格禁止使用「您需要...嗎？」這類問句！"
        ))
        msg_list = [sys_prompt] + valid_messages
        suggester_llm = llm.with_structured_output(SuggestionResponse)
        response = await suggester_llm.ainvoke(msg_list)
        return {"messages": [AIMessage(content=response.model_dump_json(), additional_kwargs={"is_suggestions": True})]}

    tool_node = ToolNode(_mcp_tools)
    
    def supervisor_router(state: MessagesState) -> list[str]:
        last_msg = state["messages"][-1]
        next_node = last_msg.additional_kwargs.get("next_node", "FINISH")
        if next_node == "FINISH":
            return [END]
        if next_node == "reporter":
            return ["reporter", "suggester"]
        if next_node == "info_agent":
            return ["info_agent", "suggester"]
        return [next_node]

    def retriever_router(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return "supervisor"

    workflow = StateGraph(MessagesState)
    
    workflow.add_node("supervisor", run_supervisor)
    workflow.add_node("info_agent", run_info_agent)
    workflow.add_node("retriever", run_retriever)
    workflow.add_node("reporter", run_reporter)
    workflow.add_node("suggester", run_suggester)
    workflow.add_node("tools", tool_node)
    
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges("supervisor", supervisor_router, {
        "retriever": "retriever",
        "reporter": "reporter",
        "info_agent": "info_agent",
        "suggester": "suggester",
        "FINISH": END
    })
    
    workflow.add_conditional_edges("retriever", retriever_router, {
        "tools": "tools",
        "supervisor": "supervisor"
    })
    workflow.add_edge("tools", "retriever")
    
    workflow.add_edge("reporter", END)
    workflow.add_edge("info_agent", END)
    workflow.add_edge("suggester", END)

    return workflow.compile()
