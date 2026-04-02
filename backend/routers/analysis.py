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


