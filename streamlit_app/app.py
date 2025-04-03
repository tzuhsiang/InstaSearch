import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging
from datetime import datetime, timedelta
from PIL import Image, UnidentifiedImageError


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
    
    # 計算預設的開始日期（一年前）
    default_start_date = datetime.now().date() - timedelta(days=365)
    
    # 日期選擇器
    start_date = st.date_input("開始日期", value=default_start_date)
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
    
    # 在側邊欄底部添加一個spacer推送設定按鈕到底部
    st.markdown("""<div style='flex-grow: 1'></div>""", unsafe_allow_html=True)
    
    # 設定按鈕（在側邊欄最底部）
    st.button("⋮", key="settings_button", help="上傳Instagram資料", use_container_width=True, 
             on_click=lambda: setattr(st.session_state, 'show_popup', True))

# 在主區域顯示彈窗
if st.session_state.get('show_popup', False):
    with st.form("settings_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔄 更新Instagram資料")
            st.markdown("---")
            
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
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.form_submit_button("關閉", use_container_width=True):
                    st.session_state.show_popup = False
                    st.rerun()
            with btn_col2:
                if st.form_submit_button("處理資料", type="primary", use_container_width=True):
                    with st.spinner('處理資料中...'):
                        import sys, os
                        sys.path.append(os.path.dirname(__file__))
                        import setup
                        success, error = setup.process_instagram_zip(save_path)
                        # 處理完成後移除路徑
                        sys.path.remove(os.path.dirname(__file__))
                        if success:
                            st.success("資料處理完成！")
                            # 關閉彈窗
                            st.session_state.show_popup = False
                            st.rerun()
                        else:
                            st.error(f"處理失敗：{error}")

# 搜尋邏輯
if st.session_state.get("search_button") and es is not None:
        # 重設頁碼
        st.session_state.current_page = 1
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

                # 存儲搜尋結果到 session_state
                st.session_state.search_results = response.get("hits", {}).get("hits", [])
            except Exception as e:
                st.error(f"搜尋時發生錯誤: {e}")
        else:
            st.error("請至少輸入關鍵字或選擇時間！")

# 初始化頁碼（如果需要）
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# 顯示搜尋結果（如果存在）
if hasattr(st.session_state, 'search_results'):
    hits = st.session_state.search_results
    if hits:
        total_hits = len(hits)
        st.success(f"找到 {total_hits} 筆結果")
        
        # 分頁設定
        items_per_page = 10
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
                
                # 讀取圖片路徑，存進清單
                image_list = []
                media = result["_source"].get('media', [])

                if media:
                    for item in media:
                        # 從ES中獲取相對路徑
                        image_path = item.get('uri', '')
                        # 將相對路徑轉換為容器內的絕對路徑
                        if image_path and not image_path.startswith('/'):
                            image_path = os.path.join('/app', image_path)
                        if os.path.exists(image_path):
                            try:
                                # 嘗試開啟並驗證圖片檔案是否正常
                                with Image.open(image_path) as img:
                                    img.verify()  # verify() 不會回傳圖片，但可驗證檔案是否損壞
                                image_list.append(image_path)
                            except UnidentifiedImageError:
                                st.error(f"無法識別圖片檔案：{image_path}")
                            except Exception as e:
                                st.error(f"讀取圖片 {image_path} 時發生錯誤：{e}")
                        else:
                            st.error(f"找不到圖片：{image_path}")

                st.subheader(title)
                st.write(content)
                
                # 若 image_list 不為空，則顯示所有圖片
                if image_list:
                    st.image(image_list, width=300)  # 可依需求調整寬度或其他參數
                
                st.markdown("---")  # 分隔線

    else:
        st.warning("沒有找到相關結果")
