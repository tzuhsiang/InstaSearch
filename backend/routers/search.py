from fastapi import APIRouter, Query, HTTPException
from database import get_es_client
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SearchResult(BaseModel):
    id: str
    datetime: Optional[str]
    content: Optional[str]
    media: List[Dict[str, Any]]
    score: float

class SearchResponse(BaseModel):
    total: int
    page: int
    pages: int
    results: List[SearchResult]

@router.get("/", response_model=SearchResponse)
def search_posts(
    q: Optional[str] = None,
    start_date: Optional[str] = None, # ISO format YYYY-MM-DD
    end_date: Optional[str] = None,
    page: int = 1,
    size: int = 10
):
    es = get_es_client()
    must_conditions = []

    if q:
        must_conditions.append({"match": {"content": q}})
    
    if start_date or end_date:
        date_range = {"range": {"datetime": {}}}
        if start_date:
            date_range["range"]["datetime"]["gte"] = f"{start_date}T00:00:00+00:00"
        if end_date:
            date_range["range"]["datetime"]["lte"] = f"{end_date}T23:59:59+00:00"
        must_conditions.append(date_range)
    
    # Sort by datetime desc
    query_body = {
        "query": {"bool": {"must": must_conditions}},
        "sort": [{"datetime": {"order": "desc"}}],
        "from": (page - 1) * size,
        "size": size
    }

    try:
        if not es.ping():
             raise HTTPException(status_code=503, detail="Elasticsearch not available")

        # Use tracked_total_hits to get accurate count
        res = es.search(index="ig_data", body=query_body, track_total_hits=True)
        hits_data = res.get("hits", {})
        hits = hits_data.get("hits", [])
        total_hits = hits_data.get("total", {}).get("value", 0)
        
        results = []
        for hit in hits:
            source = hit["_source"]
            processed_media = []
            for m in source.get("media", []):
                uri = m.get("uri", "")
                # Normalize path for frontend
                if uri.startswith("ig_data/"):
                     m["url"] = f"/images/{uri}"
                elif uri.startswith("media/"):
                     m["url"] = f"/images/{uri}"
                else:
                     # If it's a local path like /app/ig_data/..., strip /app/ or similar
                     if "ig_data" in uri:
                         # try to extract part after ig_data
                         part = uri.split("ig_data")[-1]
                         m["url"] = f"/images/ig_data{part}"
                     else:
                         m["url"] = uri 
                processed_media.append(m)
            
            results.append(SearchResult(
                id=hit["_id"],
                datetime=source.get("datetime"),
                content=source.get("content"),
                media=processed_media,
                score=hit["_score"] or 0.0
            ))
            
        return SearchResponse(
            total=total_hits,
            page=page,
            pages=(total_hits + size - 1) // size,
            results=results
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
