from fastapi import APIRouter, HTTPException
from database import get_es_client
import requests
import os
import logging
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/trend")
def get_trend():
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
         if not es.ping():
             raise HTTPException(status_code=503, detail="Elasticsearch not available")
             
         res = es.search(index="ig_data", body=agg_query)
         buckets = res['aggregations']['posts_over_time']['buckets']
         data = [{"date": datetime.fromtimestamp(b['key']/1000).strftime('%Y-%m'), "count": b['doc_count']} for b in buckets]
         return {"data": data}
    except Exception as e:
        logger.error(f"Trend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AnalyzeRequest(BaseModel):
    content: str

@router.post("/post")
def analyze_post(req: AnalyzeRequest):
    api_url = os.getenv("LANGFLOW_API_1")
    if not api_url:
        raise HTTPException(status_code=500, detail="LANGFLOW_API_1 not configured")
    
    try:
        headers = {"Content-Type": "application/json"}
        # Langflow expects "input" usually, or whatever the component expects
        data = {"input": req.content}
        
        # Check if URL is valid
        if not api_url.startswith("http"):
            # Could be internal service name
            pass 

        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        content = response.json()
        
        if "outputs" in content and content["outputs"]:
             try:
                 # Deep path traversal
                 result = content["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                 return {"result": result}
             except (KeyError, IndexError, TypeError):
                 return {"result": "Parsing error", "raw": content}
        else:
             return {"result": "No output", "raw": content}

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
