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
from langgraph.checkpoint.memory import MemorySaver

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
    
    # 手動注入 UI 控制工具
    async def _update_ui_arun(query: str, start_date: str = None, end_date: str = None) -> str:
        return f"已發送 UI 更新指令：搜尋「{query}」，時間範圍「{start_date} ~ {end_date}」"

    ui_tool = StructuredTool.from_function(
        name="update_search_ui",
        description="更新前端搜尋介面的關鍵字與日期範圍。當使用者要求「搜尋」、「找看看」或者是「顯示最近...的資料」時，請務必呼叫此工具同步更新介面。",
        func=lambda query, start_date=None, end_date=None: "Synchronous execution not supported",
        coroutine=_update_ui_arun
    )
    _mcp_tools.append(ui_tool)

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
            "你是 Instagram 食記分析的主管 (Supervisor)。負責決定下一個要執行的部門。\n"
            "1. 需要深入查詢 IG 貼文、尋找餐廳或更新搜尋介面：交給 'retriever'。\n"
            "2. 如果已經呼叫過工具且已獲得結果，或者已經更新了搜尋介面 (update_search_ui)，請交給 'reporter' 向使用者確認。\n"
            "3. 如果使用者單純閒聊、打招呼或是詢問『系統有哪些功能』：交給 'info_agent'。\n"
            "4. 任務已完全達成且已回覆使用者：選擇 'FINISH'。\n"
            "請判斷使用者是否真的需要『詳細分析報告』，若只是單純『搜尋』，請確保下一個流程保持簡短。"
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
        
        # 訊息修剪 (Message Pruning): 只保留使用者最後的需求、系統指令與最近的工具結果
        # 避免將所有過往的中間思考與冗餘過程塞入最終報告生成
        pruned = []
        for m in reversed(messages):
            if isinstance(m, SystemMessage) or isinstance(m, HumanMessage):
                pruned.insert(0, m)
                if len([x for x in pruned if isinstance(x, HumanMessage)]) >= 2: break
            elif isinstance(m, ToolMessage):
                pruned.insert(0, m)
            elif isinstance(m, AIMessage) and m.tool_calls:
                pruned.insert(0, m)
        
        # 檢查是否剛執行過 UI 更新
        ui_updated = any(isinstance(m, ToolMessage) and m.name == "update_search_ui" for m in messages)
        
        sys_prompt = SystemMessage(content=(
            "你是資深 IG 食記編輯員 (Reporter)。你的任務是彙整資訊回報給使用者。\n"
            "【關鍵原則】\n"
            "1. 原則：如果對話中剛呼叫過 `update_search_ui` 且使用者指示為搜尋性質，請保持回覆為『一句話確認』即可，直接告知『已為您更新介面...』，不要輸出長篇 Markdown 報告。\n"
            "2. 深度分析：只有在使用者要求『分析』、『整理評價』、『寫文章』時，才需產生專業的 Markdown 報告。\n"
            "3. 避免重複：不要在聊天視窗中重複列出左側搜尋結果已經看得到的內容。"
        ))
        msg_list = [sys_prompt] + pruned
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

    async def run_reflector(state: MessagesState):
        """[EXPERIMENTAL] 修復工具呼叫失敗或無結果的狀況"""
        messages = state["messages"]
        last_msg = messages[-1]
        error_content = last_msg.content if isinstance(last_msg, ToolMessage) else "未知錯誤"
        
        sys_prompt = SystemMessage(content=(
            "你是錯誤診斷與修正專員 (Reflector)。\n"
            f"前一個工具執行失敗，錯誤為：{error_content}\n"
            "請分析錯誤原因（如：格式不對、日期範圍無資料），並對使用者原本的需求進行微調，重新交給 retriever 嘗試。"
        ))
        msg_list = [sys_prompt] + messages
        response = await llm.ainvoke(msg_list)
        return {"messages": [response]}

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
    workflow.add_node("reflector", run_reflector)
    workflow.add_node("tools", tool_node)
    
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges("supervisor", supervisor_router, {
        "retriever": "retriever",
        "reporter": "reporter",
        "info_agent": "info_agent",
        "suggester": "suggester",
        "FINISH": END
    })
    
    def tool_exit_router(state: MessagesState) -> str:
        last_msg = state["messages"][-1]
        # Check for empty or error content
        content = str(last_msg.content)
        if "Error" in content or "無資料" in content or len(content) < 5:
             return "reflector"
        # 效能優化：如果已經呼叫過 UI 更新且是搜尋操作，直接給 reporter
        history = state["messages"]
        for msg in reversed(history[-3:]):
            if isinstance(msg, ToolMessage) and msg.name == "update_search_ui":
                return "reporter"
        return "retriever"

    workflow.add_conditional_edges("retriever", retriever_router, {
        "tools": "tools",
        "supervisor": "supervisor"
    })
    workflow.add_conditional_edges("tools", tool_exit_router, {
        "reflector": "reflector",
        "reporter": "reporter",
        "retriever": "retriever"
    })
    workflow.add_edge("reflector", "retriever")
    
    workflow.add_edge("reporter", END)
    workflow.add_edge("info_agent", END)
    workflow.add_edge("suggester", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
