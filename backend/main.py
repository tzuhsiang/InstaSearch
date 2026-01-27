from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import search, analysis, settings, mcp_server
from contextlib import asynccontextmanager
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure directories exist
    os.makedirs("ig_data", exist_ok=True)
    os.makedirs("media", exist_ok=True)
    yield
    # Shutdown

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

# Include routers
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(mcp_server.router, prefix="/mcp", tags=["mcp"]) # Expose MCP at root/mcp or similar

@app.get("/health")
def health_check():
    return {"status": "ok"}
