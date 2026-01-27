from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

class Settings(BaseModel):
    langflow_url: str
    langflow_api_1: str

@router.get("/", response_model=Settings)
def get_settings():
    return Settings(
        langflow_url=os.getenv("LANGFLOW_URL", "http://langflow:7860"),
        langflow_api_1=os.getenv("LANGFLOW_API_1", "")
    )

@router.post("/")
def update_settings(settings: Settings):
    env_path = "env/app.env" 
    
    try:
        lines = [
            f'LANGFLOW_URL="{settings.langflow_url}"',
            f'LANGFLOW_API_1="{settings.langflow_api_1}"'
        ]
        
        # Verify directory exists
        if not os.path.exists("env"):
             os.makedirs("env", exist_ok=True)
        
        with open(env_path, "w") as f:
            f.write("\n".join(lines))
            
        # Reload current process env
        os.environ["LANGFLOW_URL"] = settings.langflow_url
        os.environ["LANGFLOW_API_1"] = settings.langflow_api_1
        
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
