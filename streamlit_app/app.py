import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging

# 設定 log 格式
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/streamlit_app.log"),  # 📌 存到 logs/streamlit_app.log
        logging.StreamHandler()  # 同時顯示在終端機
    ]
)

logger = logging.getLogger(__name__)
logger.info("✅ 成功初始化 Logging 系統！")



import os
es_host = os.getenv("ES_HOST", "http://elasticsearch:9200")  # 預設使用容器內部連線


# 嘗試連接 Elasticsearch（重試 5 次）
MAX_RETRIES = 5
RETRY_INTERVAL = 5  # 每次重試間隔 5 秒

es = None
for i in range(MAX_RETRIES):
    try:
        es = Elasticsearch([es_host])
        if es.ping():
            logger.info("✅ 成功連接到 Elasticsearch！")  # ✅ 只記錄日誌，不顯示在介面
            break
    except Exception as e:
        st.warning(f"🚨 連接 Elasticsearch 失敗，重試中 ({i+1}/{MAX_RETRIES})... 等待 {RETRY_INTERVAL} 秒")
        time.sleep(RETRY_INTERVAL)
else:
    st.error("❌ 無法連接到 Elasticsearch，請檢查服務是否運行中！")

# 設定 Streamlit 介面標題
st.title("🔍 Elasticsearch 搜尋介面")

# 建立輸入框，讓使用者輸入關鍵字
query = st.text_input("請輸入搜尋關鍵字", "")

# 當使用者按下搜尋按鈕時執行搜尋
if st.button("搜尋") and es is not None:
    if query:
        # 執行 Elasticsearch 搜尋
        search_body = {
            "query": {
                "match": {
                    "content": query  # 假設索引中有 "content" 欄位
                }
            }
        }

        try:
            with st.spinner('搜尋中...'):
                response = es.search(index="text_experiment", body=search_body)

            # 顯示搜尋結果
            hits = response.get("hits", {}).get("hits", [])
            
            if hits:
                st.success(f"找到 {len(hits)} 筆結果")
                for result in hits:
                    title = result["_source"].get("title", "無標題")
                    content = result["_source"].get("content", "無內容")
                    st.subheader(title)
                    st.write(content)
                    st.markdown("---")  # 分隔線
            else:
                st.warning("沒有找到相關結果")
        except Exception as e:
            st.error(f"搜尋時發生錯誤: {e}")
    else:
        st.error("請輸入搜尋關鍵字！")
