import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging

# 設定頁面配置
st.set_page_config(
    page_title="Elasticsearch 搜尋介面",
    layout="wide",  # 使用寬屏布局
    initial_sidebar_state="expanded"
)

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
st.title("🔍 IG食記搜尋介面")

# 側邊欄搜尋條件
# 設定側邊欄寬度
st.markdown(
    """
    <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 300px;
            max-width: 300px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("搜尋條件")
    # 建立輸入框，讓使用者輸入關鍵字
    query = st.text_input("請輸入搜尋關鍵字", "")
    
    # 日期選擇器
    start_date = st.date_input("開始日期")
    end_date = st.date_input("結束日期")
    
    # 組合日期範圍（使用 ISO 8601 格式）
    start_datetime = None
    end_datetime = None
    if start_date:
        start_datetime = f"{start_date.isoformat()}T00:00:00+00:00"
    if end_date:
        end_datetime = f"{end_date.isoformat()}T23:59:59+00:00"
    
    # 搜尋按鈕
    st.button("搜尋", use_container_width=True, key="search_button")

# 搜尋邏輯
if st.session_state.get("search_button") and es is not None:
        if query or start_datetime:
            # 建立搜尋條件
            must_conditions = []
            
            if query:
                must_conditions.append({
                    "match": {
                        "content": query
                    }
                })
            
            if start_datetime or end_datetime:
                date_range = {
                    "range": {
                        "datetime": {}
                    }
                }
                if start_datetime:
                    date_range["range"]["datetime"]["gte"] = start_datetime
                if end_datetime:
                    date_range["range"]["datetime"]["lte"] = end_datetime
                must_conditions.append(date_range)

            # 執行 Elasticsearch 搜尋
            search_body = {
                "query": {
                    "bool": {
                        "must": must_conditions
                    }
                },
                "sort": [
                    {"datetime": {"order": "desc"}}  # 從新到舊排序
                ]
            }

            try:
                with st.spinner('搜尋中...'):
                    response = es.search(
                        index="ig_data",
                        body=search_body,
                        size=10000  # 設定較大的結果數量限制
                    )

                # 顯示搜尋結果
                hits = response.get("hits", {}).get("hits", [])
                
                if hits:
                    st.success(f"找到 {len(hits)} 筆結果")
                    for result in hits:
                        with st.container():
                            title = result["_source"].get("datetime", "無標題")
                            content = result["_source"].get("content", "無內容")
                            st.subheader(title)
                            st.write(content)
                            st.markdown("---")  # 分隔線
                else:
                    st.warning("沒有找到相關結果")
            except Exception as e:
                st.error(f"搜尋時發生錯誤: {e}")
        else:
            st.error("請至少輸入關鍵字或選擇時間！")
