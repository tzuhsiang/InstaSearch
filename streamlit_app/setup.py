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

# 定義常數
BASE_DIR = "/app"
IG_DATA_DIR = os.path.join(BASE_DIR, "ig_data")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
EXTRACT_PATH = os.path.join(IG_DATA_DIR, "tmp_extract")
POSTS_JSON_PATH = os.path.join(EXTRACT_PATH, "your_instagram_activity", "content", "posts_1.json")
ES_HOST = "http://elasticsearch:9200"
ES_INDEX = "ig_data"

# 初始化logging（先不建立檔案，等目錄檢查完成後再設定）
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

@contextmanager
def elasticsearch_client():
    """建立Elasticsearch客戶端的上下文管理器"""
    client = Elasticsearch(ES_HOST)
    try:
        yield client
    finally:
        client.close()

def check_directory_structure():
    """檢查並建立必要的目錄結構"""
    try:
        # 首先創建所有必要的目錄
        directories = [IG_DATA_DIR, MEDIA_DIR, LOGS_DIR]
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                # 確保目錄權限
                os.chmod(directory, 0o777)
                logger.info(f"建立/更新目錄權限：{directory}")
            except Exception as e:
                raise PermissionError(f"無法創建或修改目錄 {directory}: {e}")

        # 檢查每個目錄的寫入權限
        for directory in directories:
            try:
                test_file = os.path.join(directory, '.test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                raise PermissionError(f"目錄 {directory} 無法寫入: {e}")

        # 確認所有目錄都存在且可寫入後，添加檔案日誌處理器
        file_handler = logging.FileHandler(os.path.join(LOGS_DIR, "setup.log"))
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
                
        logger.info("✅ 目錄結構檢查完成")
        return True
    except Exception as e:
        logger.error(f"❌ 目錄結構檢查失敗: {e}")
        raise

def find_zip_file(zip_path: str = None) -> str:
    """尋找zip檔案
    
    Args:
        zip_path: 指定的zip檔案路徑，如果未指定則尋找ig_data目錄中唯一的zip檔案
    
    Returns:
        str: zip檔案的完整路徑
    
    Raises:
        FileNotFoundError: 當找不到zip檔案時
    """
    if zip_path and os.path.exists(zip_path):
        return zip_path
        
    if not os.path.exists(IG_DATA_DIR):
        raise FileNotFoundError(f"目錄 {IG_DATA_DIR} 不存在")
    
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
    try:
        # 創建並設置臨時目錄權限
        os.makedirs(EXTRACT_PATH, exist_ok=True)
        os.chmod(EXTRACT_PATH, 0o777)
        logger.info(f"創建臨時目錄：{EXTRACT_PATH}")
        
        # 解壓檔案
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_PATH)
        
        # 設置解壓後目錄的權限
        for root, dirs, files in os.walk(EXTRACT_PATH):
            # 設置目錄權限
            for d in dirs:
                dir_path = os.path.join(root, d)
                os.chmod(dir_path, 0o777)
            # 設置檔案權限
            for f in files:
                file_path = os.path.join(root, f)
                os.chmod(file_path, 0o666)
        
        logger.info("✅ 解壓完成並設置權限")
    except Exception as e:
        logger.error(f"解壓或設置權限時發生錯誤: {e}")
        raise

def process_instagram_data() -> List[Dict]:
    """處理Instagram JSON資料
    
    Returns:
        List[Dict]: 處理後的Instagram資料列表
    
    Raises:
        FileNotFoundError: 當找不到posts_1.json檔案時
    """
    if not os.path.exists(POSTS_JSON_PATH):
        raise FileNotFoundError(f"找不到檔案：{POSTS_JSON_PATH}")
        
    with open(POSTS_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    content = []
    for item in data:
        try:
            # 修改media路徑，添加posts前綴
            media_list = item.get("media", [])
            processed_media = []
            for media_item in media_list:
                uri = media_item.get("uri", "")
                if uri:
                    # 確保路徑以posts開頭
                    if not uri.startswith("posts/"):
                        uri = f"posts/{uri}"
                    # 更新為完整的media路徑
                    media_item["uri"] = os.path.join("media", uri)
                processed_media.append(media_item)
                
            content.append({
                "media": processed_media,
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
    media_dir = os.path.join(EXTRACT_PATH, "media")
    posts_dir = os.path.join(media_dir, "posts")
    if os.path.exists(posts_dir):
        try:
            # 清空或創建目標目錄
            if os.path.exists(MEDIA_DIR):
                shutil.rmtree(MEDIA_DIR)
            os.makedirs(MEDIA_DIR, exist_ok=True)
            os.chmod(MEDIA_DIR, 0o777)
            
            # 直接複製整個posts目錄到media目錄
            target_posts_dir = os.path.join(MEDIA_DIR, "posts")
            logger.info(f"開始複製檔案從 {posts_dir} 到 {target_posts_dir}")
            shutil.copytree(posts_dir, target_posts_dir)
            
            # 設置所有複製後檔案的權限
            for root, dirs, files in os.walk(target_posts_dir):
                # 設置目錄權限
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    os.chmod(dir_path, 0o777)
                # 設置檔案權限
                for f in files:
                    file_path = os.path.join(root, f)
                    os.chmod(file_path, 0o666)
                    
            logger.info("複製完成並設置權限")
        except Exception as e:
            logger.error(f"移動檔案時發生錯誤: {e}")
            # 如果發生錯誤，確保目標目錄存在並有正確權限
            os.makedirs(MEDIA_DIR, exist_ok=True)
            os.chmod(MEDIA_DIR, 0o777)
            raise
        logger.info(f"📁 資料已搬移到 {MEDIA_DIR} 並設置適當權限")
    
    # 清除暫存
    if os.path.exists(EXTRACT_PATH):
        shutil.rmtree(EXTRACT_PATH)
    
    # 清除JSON檔案
    json_file = os.path.join(IG_DATA_DIR, "ig_data.json")
    if os.path.exists(json_file):
        os.remove(json_file)
        logger.info(f"已刪除：{json_file}")

def process_instagram_zip(zip_path: str = None) -> tuple[bool, str]:
    """處理Instagram ZIP檔案的主要函數
    
    Args:
        zip_path: 指定的zip檔案路徑，如果未指定則尋找ig_data目錄中唯一的zip檔案
        
    Returns:
        tuple[bool, str]: (是否成功, 錯誤訊息)
    """
    try:
        # 檢查目錄結構和權限
        check_directory_structure()
        
        zip_path = find_zip_file(zip_path)
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
        
        return True, None
        
    except Exception as e:
        error_msg = f"程序執行過程中發生錯誤: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

if __name__ == "__main__":
    process_instagram_zip()
