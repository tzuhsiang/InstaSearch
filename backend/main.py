from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import search, analysis, settings, mcp_server, api_mcp_server, chat
from contextlib import asynccontextmanager
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_agent_background():
    from agent import init_mcp_client, build_graph
    import asyncio
    from routers import chat
    for attempt in range(15):
        try:
            await init_mcp_client()
            break
        except Exception as e:
            if attempt < 14:
                logger.warning(f"⏳ MCP Server 尚未就緒，重試中... ({attempt+1}/15)")
                await asyncio.sleep(3)
            else:
                logger.error(f"❌ MCP Server 連線失敗：{e}")
    try:
        chat.router.agent_graph = build_graph()
        logger.info("✅ LangGraph Agent initialized")
    except Exception as e:
        logger.error(f"❌ Failed to build graph: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure directories exist
    os.makedirs("ig_data", exist_ok=True)
    os.makedirs("media", exist_ok=True)
    
    import asyncio
    asyncio.create_task(init_agent_background())
    
    yield
    # Shutdown
    from agent import close_mcp_client
    await close_mcp_client()

app = FastAPI(title="InstaSearch API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static mounts for images
# Access via http://host:8000/images/ig_data/... or /images/media/...
app.mount("/images/ig_data", StaticFiles(directory="ig_data"), name="ig_data")
app.mount("/images/media", StaticFiles(directory="media"), name="media")

# Mount standalone agent testing page
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Include routers
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(mcp_server.router, prefix="/mcp", tags=["mcp"]) # Expose MCP at root/mcp or similar
app.include_router(api_mcp_server.router, prefix="/api-mcp", tags=["api-mcp"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
