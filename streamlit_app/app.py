import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging
from datetime import datetime, timedelta
from PIL import Image, UnidentifiedImageError
import os

# 設定頁面配置
st.set_page_config(
    page_title="IG食記搜尋系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設定 CSS 樣式
st.markdown(
    """
    <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 300px;
            max-width: 300px;
        }
        div[data-testid="stVerticalBlock"] > div:has(div.stButton) > div {
            padding-top: 25px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 設定 log 格式
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/streamlit_app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("✅ 成功初始化 Logging 系統！")

# Elasticsearch 連接設定
es_host = os.getenv("ES_HOST", "http://elasticsearch:9200")

# 嘗試連接 Elasticsearch（重試 5 次）
MAX_RETRIES = 5
RETRY_INTERVAL = 5

es = None
for i in range(MAX_RETRIES):
    try:
        es = Elasticsearch([es_host])
        if es.ping():
            logger.info("✅ 成功連接到 Elasticsearch！")
            break
    except Exception as e:
        st.warning(f"🚨 連接 Elasticsearch 失敗，重試中 ({i+1}/{MAX_RETRIES})... 等待 {RETRY_INTERVAL} 秒")
        time.sleep(RETRY_INTERVAL)
else:
    st.error("❌ 無法連接到 Elasticsearch，請檢查服務是否運行中！")

# 初始化 session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'active_page' not in st.session_state:
    st.session_state.active_page = "搜尋"

def change_page(page):
    st.session_state.active_page = page
    st.session_state.current_page = 1

# 側邊欄導航
with st.sidebar:
    st.title("選單")
    
    # 使用一般按鈕
    if st.button("🔍 搜尋", use_container_width=True):
        change_page("搜尋")
    
    if st.button("📊 分析", use_container_width=True):
        change_page("分析")
    
    if st.button("⚙️ 設置", use_container_width=True):
        change_page("設置")

def search_page():
    st.title("🔍 搜尋")
    
    # 所有搜尋控制項在同一列
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 3, 1])
    
    with col1:
        default_start_date = datetime.now().date() - timedelta(days=365)
        start_date = st.date_input("開始日期", value=default_start_date)
    
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

        # 組合日期範圍
        start_datetime = f"{start_date.isoformat()}T00:00:00+00:00" if start_date else None
        end_datetime = f"{end_date.isoformat()}T23:59:59+00:00" if end_date else None

        # 搜尋邏輯
        must_conditions = []
        if query:
            must_conditions.append({"match": {"content": query}})
        if start_datetime or end_datetime:
            date_range = {"range": {"datetime": {}}}
            if start_datetime:
                date_range["range"]["datetime"]["gte"] = start_datetime
            if end_datetime:
                date_range["range"]["datetime"]["lte"] = end_datetime
            must_conditions.append(date_range)

        try:
            with st.spinner('搜尋中...'):
                response = es.search(
                    index="ig_data",
                    body={
                        "query": {"bool": {"must": must_conditions}},
                        "sort": [{"datetime": {"order": "desc"}}]
                    },
                    size=10000
                )
                hits = response.get("hits", {}).get("hits", [])
                
                if hits:
                    st.success(f"找到 {len(hits)} 筆結果")
                    display_results(hits)
                else:
                    st.warning("沒有找到相關結果")
                    
        except Exception as e:
            st.error(f"搜尋時發生錯誤: {e}")

def analyze_page():
    st.title("📊 分析")
    
    if es:
        try:
            # 取得時間分佈
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
            
            # 處理資料用於圖表顯示
            dates = []
            counts = []
            
            for bucket in response['aggregations']['posts_over_time']['buckets']:
                dates.append(datetime.fromtimestamp(bucket['key']/1000).strftime('%Y-%m'))
                counts.append(bucket['doc_count'])
            
            # 顯示圖表
            st.subheader("發文時間分布")
            st.line_chart(dict(zip(dates, counts)))
            
            # 計算總發文數
            st.metric("總發文數", len(dates))
            
        except Exception as e:
            st.error(f"分析資料時發生錯誤: {e}")
    else:
        st.error("無法連接到資料庫")

def settings_page():
    st.title("⚙️ 設置")
    
    st.subheader("🔄 更新Instagram資料")
    
    uploaded_file = st.file_uploader("請選擇ZIP檔案", type="zip", 
                                   help="上傳Instagram資料下載的ZIP檔案")
    
    if uploaded_file is not None:
        # 確保ig_data目錄存在
        ig_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ig_data")
        os.makedirs(ig_data_path, exist_ok=True)
        
        # 儲存上傳的檔案
        save_path = os.path.join(ig_data_path, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("處理資料", type="primary"):
            with st.spinner('處理資料中...'):
                import sys
                sys.path.append(os.path.dirname(__file__))
                import setup
                success, error = setup.process_instagram_zip(save_path)
                sys.path.remove(os.path.dirname(__file__))
                
                if success:
                    st.success("資料處理完成！")
                else:
                    st.error(f"處理失敗：{error}")

def display_results(hits):
    # 分頁設定
    items_per_page = 10
    total_hits = len(hits)
    total_pages = (total_hits + items_per_page - 1) // items_per_page
    
    # 分頁導航
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

    # 計算當前頁的資料範圍
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_hits)

    # 顯示當前頁的資料
    for result in hits[start_idx:end_idx]:
        with st.container():
            title = result["_source"].get("datetime", "無標題")
            content = result["_source"].get("content", "無內容")
            
            # 讀取圖片
            image_list = []
            media = result["_source"].get('media', [])
            
            if media:
                for item in media:
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

            st.subheader(title)
            st.write(content)
            
            if image_list:
                st.image(image_list, width=300)
            
            st.markdown("---")

# 根據選擇的頁面顯示內容
if st.session_state.active_page == "搜尋":
    search_page()
elif st.session_state.active_page == "分析":
    analyze_page()
else:
    settings_page()
