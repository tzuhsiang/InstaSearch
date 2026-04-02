import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", "env", "app.env")
load_dotenv(dotenv_path=env_path, override=True)

# Azure OpenAI 設定
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o") # default

import json

mcp_servers_path = os.path.join(os.path.dirname(__file__), "mcp_servers.json")
MCP_SERVERS_DICT = {}
try:
    with open(mcp_servers_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for name, info in data.get("servers", {}).items():
            if "url" in info:
                MCP_SERVERS_DICT[name] = info["url"]
except Exception as e:
    # 預設 Fallback
    MCP_SERVERS_DICT = {
        "instagram": "http://127.0.0.1:8000/mcp/sse",
        "system_api": "http://127.0.0.1:8000/api-mcp/sse"
    }

# 預設推薦問題設定
default_sugg_str = os.getenv(
    "DEFAULT_SUGGESTIONS", 
    "最新信義區食記有哪些？,有推薦的高級牛排館嗎？,過去一年的食記發文趨勢是如何？"
)
DEFAULT_SUGGESTIONS = [s.strip() for s in default_sugg_str.split(",") if s.strip()]
