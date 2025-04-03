import zipfile
import os
import shutil
import json
import pandas as pd
import datetime
from elasticsearch import Elasticsearch
from contextlib import contextmanager
from typing import Dict, List
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定義常數
BASE_DIR = "."
IG_DATA_DIR = os.path.join(BASE_DIR, "ig_data")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
EXTRACT_PATH = os.path.join(IG_DATA_DIR, "tmp_extract")
POSTS_JSON_PATH = os.path.join(EXTRACT_PATH, "your_instagram_activity", "content", "posts_1.json")
ES_HOST = "http://localhost:9200"
ES_INDEX = "ig_data"

@contextmanager
def elasticsearch_client():
    """建立Elasticsearch客戶端的上下文管理器"""
    client = Elasticsearch(ES_HOST)
    try:
        yield client
    finally:
        client.close()

def find_zip_file() -> str:
    """尋找ig_data目錄中唯一的zip檔案
    
    Returns:
        str: zip檔案的完整路徑
    
    Raises:
        FileNotFoundError: 當找不到zip檔案或有多個zip檔案時
    """
    zip_files = [f for f in os.listdir(IG_DATA_DIR) if f.endswith('.zip')]
    if len(zip_files) != 1:
        raise FileNotFoundError("找不到唯一的 zip 檔案，請確認目錄中只有一個 zip 檔")
    
    return os.path.join(IG_DATA_DIR, zip_files[0])

def extract_zip(zip_path: str):
    """解壓縮Instagram資料檔案
    
    Args:
        zip_path: zip檔案的路徑
    """
    logger.info(f"正在處理：{zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_PATH)

def process_instagram_data() -> List[Dict]:
    """處理Instagram JSON資料
    
    Returns:
        List[Dict]: 處理後的Instagram資料列表
    """
    with open(POSTS_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    content = []
    for item in data:
        try:
            content.append({
                "media": item["media"],
                "title": item["title"].encode('latin1').decode('utf-8'),
                "creation_timestamp": datetime.datetime.fromtimestamp(item["creation_timestamp"]).isoformat()
            })
        except (KeyError, UnicodeError) as e:
            logger.warning(f"處理資料時發生錯誤: {str(e)}")
            continue

    return content

def setup_elasticsearch_index():
    """設置Elasticsearch索引"""
    with elasticsearch_client() as es:
        if not es.ping():
            raise ConnectionError("無法連接到Elasticsearch")
        
        logger.info("✅ 成功連接 Elasticsearch")

        # 如果索引已經存在，則刪除
        if es.indices.exists(index=ES_INDEX):
            es.indices.delete(index=ES_INDEX)

        # 創建新索引
        es.indices.create(index=ES_INDEX, body={
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "creation_timestamp": {"type": "date"}
                }
            }
        })
        logger.info(f"✅ 索引 '{ES_INDEX}' 已建立")

def import_data_to_elasticsearch(data: List[Dict]):
    """將資料導入Elasticsearch
    
    Args:
        data: 要導入的資料列表
    """
    with elasticsearch_client() as es:
        for item in data:
            doc = {
                "content": item["title"],
                "datetime": item["creation_timestamp"],
                "timestamp": datetime.datetime.now().isoformat(),
                "media": item["media"]
            }
            res = es.index(index=ES_INDEX, body=doc)
            logger.info(f"✅ 文本已寫入，ID: {res['_id']}")

def cleanup():
    """清理暫存檔案和目錄"""
    # 搬移媒體檔案
    selected_subdir = os.path.join(EXTRACT_PATH, "media")
    if os.path.exists(selected_subdir):
        os.makedirs(MEDIA_DIR, exist_ok=True)
        if os.path.exists(MEDIA_DIR):
            shutil.rmtree(MEDIA_DIR)
        shutil.move(selected_subdir, MEDIA_DIR)
        logger.info(f"📁 資料已搬移到 {MEDIA_DIR}")
    
    # 清除暫存
    if os.path.exists(EXTRACT_PATH):
        shutil.rmtree(EXTRACT_PATH)
    
    # 清除JSON檔案
    json_file = os.path.join(IG_DATA_DIR, "ig_data.json")
    if os.path.exists(json_file):
        os.remove(json_file)
        logger.info(f"已刪除：{json_file}")

def main():
    """主程序"""
    try:
        zip_path = find_zip_file()
        extract_zip(zip_path)
        
        data = process_instagram_data()
        
        # 將處理後的資料暫存為JSON
        with open(os.path.join(IG_DATA_DIR, "ig_data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info("List 已成功存到 ig_data.json 檔案中！")
        
        setup_elasticsearch_index()
        import_data_to_elasticsearch(data)
        
        cleanup()
        logger.info("✅ 初始化完成")
        
    except Exception as e:
        logger.error(f"程序執行過程中發生錯誤: {str(e)}")
        raise

if __name__ == "__main__":
    main()
