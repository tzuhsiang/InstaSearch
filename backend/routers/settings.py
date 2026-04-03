from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

class Settings(BaseModel):
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_deployment_name: str

@router.get("/", response_model=Settings)
def get_settings():
    return Settings(
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME", "")
    )

@router.post("/")
def update_settings(settings: Settings):
    env_path = "env/app.env" 
    
    try:
        # Load existing env vars to append/replace safely
        # To be simpler, we will just rewrite or ensure these are updated
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if not line.startswith("AZURE_OPENAI"):
                        lines.append(line.strip())
        
        lines.append(f'AZURE_OPENAI_API_KEY="{settings.azure_openai_api_key}"')
        lines.append(f'AZURE_OPENAI_ENDPOINT="{settings.azure_openai_endpoint}"')
        lines.append(f'AZURE_DEPLOYMENT_NAME="{settings.azure_deployment_name}"')
        
        if not os.path.exists("env"):
             os.makedirs("env", exist_ok=True)
        
        with open(env_path, "w") as f:
            f.write("\n".join(lines))
            
        os.environ["AZURE_OPENAI_API_KEY"] = settings.azure_openai_api_key
        os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
        os.environ["AZURE_DEPLOYMENT_NAME"] = settings.azure_deployment_name
        
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
