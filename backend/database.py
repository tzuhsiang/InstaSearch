from elasticsearch import Elasticsearch
import os

def get_es_client():
    es_host = os.getenv("ES_HOST", "http://elasticsearch:9200")
    return Elasticsearch([es_host])
