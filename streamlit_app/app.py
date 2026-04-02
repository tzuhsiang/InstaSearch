import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging
from datetime import datetime, timedelta
from PIL import Image
import os
import requests
from dotenv import load_dotenv

# 常數設定
CONSTANTS = {
    "ES_HOST": "http://elasticsearch:9200",
    "MAX_RETRIES": 5,
    "RETRY_INTERVAL": 5,
    "ITEMS_PER_PAGE": 10,
    "DEFAULT_DAYS_BACK": 365
}

# 頁面設定
PAGE_CONFIG = {
    "page_title": "IG食記搜尋系統",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "Get help": None,
        "Report a bug": None,
        "About": "IG食記搜尋與分析系統"
    }
}

# CSS 樣式
CSS_STYLE = """
    <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 300px;
            max-width: 300px;
        }
        div[data-testid="stVerticalBlock"] > div:has(div.stButton) > div {
            padding-top: 25px;
        }
    </style>
"""

def setup_logging():
    """設定日誌系統"""
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs/streamlit_app.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def init_elasticsearch():
    """初始化 Elasticsearch 連接"""
    es_host = os.getenv("ES_HOST", CONSTANTS["ES_HOST"])
    
    for i in range(CONSTANTS["MAX_RETRIES"]):
        try:
            es = Elasticsearch([es_host])
            if es.ping():
                logger.info("✅ 成功連接到 Elasticsearch！")
                return es
        except Exception as e:
            st.warning(f"🚨 連接 Elasticsearch 失敗，重試中 ({i+1}/{CONSTANTS['MAX_RETRIES']})... 等待 {CONSTANTS['RETRY_INTERVAL']} 秒")
            time.sleep(CONSTANTS["RETRY_INTERVAL"])
    
    st.error("❌ 無法連接到 Elasticsearch，請檢查服務是否運行中！")
    return None

def init_session_state():
    """初始化 session state"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'active_page' not in st.session_state:
        st.session_state.active_page = "搜尋"
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}

def setup_sidebar():
    """設置側邊欄"""
    with st.sidebar:
        st.title("選單")
        for page, icon in [("搜尋", "🔍"), ("分析", "📊"), ("設置", "⚙️")]:
            if st.button(f"{icon} {page}", use_container_width=True):
                st.session_state.active_page = page
                st.session_state.current_page = 1

def perform_search(es, query, start_date, end_date):
    """執行搜尋"""
    must_conditions = []
    
    if query:
        must_conditions.append({"match": {"content": query}})
    
    if start_date or end_date:
        date_range = {"range": {"datetime": {}}}
        if start_date:
            date_range["range"]["datetime"]["gte"] = f"{start_date.isoformat()}T00:00:00+00:00"
        if end_date:
            date_range["range"]["datetime"]["lte"] = f"{end_date.isoformat()}T23:59:59+00:00"
        must_conditions.append(date_range)

    try:
        response = es.search(
            index="ig_data",
            body={
                "query": {"bool": {"must": must_conditions}},
                "sort": [{"datetime": {"order": "desc"}}]
            },
            size=10000
        )
        return response.get("hits", {}).get("hits", [])
    except Exception as e:
        st.error(f"搜尋時發生錯誤: {e}")
        return []

def get_valid_images(media_list):
    """取得有效的圖片列表"""
    image_list = []
    for item in media_list:
        image_path = item.get('uri', '')
        if image_path and not image_path.startswith('/'):
            image_path = os.path.join('/app', image_path)
        if os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    img.verify()
                image_list.append(image_path)
            except Exception as e:
                logger.error(f"讀取圖片 {image_path} 時發生錯誤：{e}")
    return image_list

def display_search_result(result):
    """顯示單個搜尋結果"""
    title = result["_source"].get("datetime", "無標題")
    content = result["_source"].get("content", "無內容")
    media = result["_source"].get('media', [])
    image_list = get_valid_images(media)
    
    st.subheader(title)
    st.write(content)
    if image_list:
        st.image(image_list, width=300)
    
    st.markdown("---")

def search_page(es):
    """搜尋頁面"""
    st.title("🔍 搜尋")
    
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 3, 1])
    
    with col1:
        start_date = st.date_input(
            "開始日期",
            value=datetime.now().date() - timedelta(days=CONSTANTS["DEFAULT_DAYS_BACK"])
        )
    
    with col2:
        end_date = st.date_input("結束日期")
    
    with col3:
        query = st.text_input("請輸入搜尋關鍵字", "")
    
    with col4:
        search_button = st.button("搜尋", use_container_width=True)

    if search_button:
        if not query and not start_date:
            st.error("請至少輸入關鍵字或選擇時間！")
            return

        with st.spinner('搜尋中...'):
            hits = perform_search(es, query, start_date, end_date)
            
            if hits:
                st.success(f"找到 {len(hits)} 筆結果")
                
                # 分頁顯示
                total_pages = (len(hits) + CONSTANTS["ITEMS_PER_PAGE"] - 1) // CONSTANTS["ITEMS_PER_PAGE"]
                start_idx = (st.session_state.current_page - 1) * CONSTANTS["ITEMS_PER_PAGE"]
                end_idx = min(start_idx + CONSTANTS["ITEMS_PER_PAGE"], len(hits))
                
                # 分頁控制
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                with col1:
                    if st.button("上一頁", disabled=st.session_state.current_page <= 1):
                        st.session_state.current_page -= 1
                        st.rerun()
                with col2:
                    st.write(f"第 {st.session_state.current_page} 頁")
                with col3:
                    st.write(f"共 {total_pages} 頁")
                with col4:
                    if st.button("下一頁", disabled=st.session_state.current_page >= total_pages):
                        st.session_state.current_page += 1
                        st.rerun()
                
                # 顯示結果
                for hit in hits[start_idx:end_idx]:
                    display_search_result(hit)
            else:
                st.warning("沒有找到相關結果")

def analyze_page(es):
    """分析頁面"""
    st.title("📊 分析")
    
    if not es:
        st.error("無法連接到資料庫")
        return
        
    try:
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
        
        response = es.search(index="ig_data", body=agg_query)
        
        dates = []
        counts = []
        
        for bucket in response['aggregations']['posts_over_time']['buckets']:
            dates.append(datetime.fromtimestamp(bucket['key']/1000).strftime('%Y-%m'))
            counts.append(bucket['doc_count'])
        
        st.subheader("發文時間分布")
        st.line_chart(dict(zip(dates, counts)))
        st.metric("總發文數", len(dates))
        
    except Exception as e:
        st.error(f"分析資料時發生錯誤: {e}")

def save_env_settings():
    """儲存環境變數設定"""
    pass

def settings_page():
    """設置頁面"""
    st.title("⚙️ 設置")
    st.info("設定已移至 Vue 前端介面")

def main():
    # 初始化
    load_dotenv("env/app.env")
    global logger
    logger = setup_logging()
    logger.info("✅ 成功初始化 Logging 系統！")
    
    # 設定頁面
    st.set_page_config(**PAGE_CONFIG)
    st.markdown(CSS_STYLE, unsafe_allow_html=True)
    
    # 初始化 session state
    init_session_state()
    
    # 設置 Elasticsearch
    es = init_elasticsearch()
    
    # 設置側邊欄
    setup_sidebar()
    
    # 顯示對應頁面
    if st.session_state.active_page == "搜尋":
        search_page(es)
    elif st.session_state.active_page == "分析":
        analyze_page(es)
    else:
        settings_page()

if __name__ == "__main__":
    main()
