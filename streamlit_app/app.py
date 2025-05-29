import streamlit as st
from elasticsearch import Elasticsearch
import time
import logging
from datetime import datetime, timedelta
from PIL import Image, UnidentifiedImageError
import os
import requests
from dotenv import load_dotenv

def analyze_post_content(content):
    """使用 Langflow API 分析貼文內容"""
    api_url = os.getenv("LANGFLOW_API_1")
    if not api_url:
        logger.error("未設定 Langflow API")
        raise ValueError("未設定 Langflow API")
    
    try:
        # 準備請求數據
        request_data = {'input': content}
        logger.info(f"發送分析請求到: {api_url}")
        logger.debug(f"請求內容: {request_data}")

        # 發送請求
        response = requests.post(
            api_url,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        # 解析響應
        result = response.json()
        logger.debug(f"收到響應: {result}")

        # 直接訪問結果路徑
        try:
            text_result = result['outputs'][0]['outputs'][0]['results']['text']['text']
            if not text_result:
                raise ValueError("API 返回的結果為空")
            
            logger.info(f"成功獲取分析結果: {text_result}")
            return text_result
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"API 響應格式不正確: {str(e)}")
            logger.error(f"完整響應內容: {result}")
            return f"無效的 API 響應格式: {str(e)}"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API 請求錯誤: {str(e)}")
        return f"無法連接到分析服務: {str(e)}"
    except Exception as e:
        logger.error(f"未預期的錯誤: {str(e)}")
        return f"分析過程發生錯誤: {str(e)}"

# 載入環境變數
load_dotenv("env/app.env")

# 從環境變數讀取所有 API URL
langflow_api_1 = os.getenv("LANGFLOW_API_1")  #貼文分析

# 設定頁面配置
st.set_page_config(
    page_title="IG食記搜尋系統",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "IG食記搜尋與分析系統"
    }
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
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

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
        
        # 建立臨時目錄並儲存檔案
        os.makedirs(ig_data_path, exist_ok=True)
        upload_path = os.path.join(ig_data_path, "instagram_data.zip")
        
        # 保存上傳的檔案
        with open(upload_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        logger.info(f"已保存上傳檔案到: {upload_path}")
        
        if st.button("處理資料", type="primary"):
            with st.spinner('處理資料中...'):
                try:
                    # 嘗試在容器路徑中找到 setup.py
                    import sys
                    for search_path in [
                        '/app/setup.py',  # Docker容器中的路徑
                        os.path.join(os.path.dirname(__file__), '..', 'setup.py'),  # 相對路徑
                        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setup.py')  # 絕對路徑
                    ]:
                        logger.info(f"嘗試路徑: {search_path}")
                        if os.path.exists(search_path):
                            logger.info(f"找到 setup.py: {search_path}")
                            setup_path = search_path
                            setup_dir = os.path.dirname(setup_path)
                            
                            # 添加到 Python 路徑
                            if setup_dir not in sys.path:
                                sys.path.insert(0, setup_dir)
                                logger.info(f"添加到 Python 路徑: {setup_dir}")
                            
                            # 動態加載模組
                            import importlib.util
                            spec = importlib.util.spec_from_file_location("setup", setup_path)
                            setup = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(setup)
                            logger.info("成功載入 setup 模組")
                            break
                    else:
                        raise FileNotFoundError("在所有可能的路徑中都找不到 setup.py")
                    
                    # 處理上傳的檔案
                    success, error = setup.process_instagram_zip(upload_path)
                    
                    if success:
                        st.success("✅ 資料處理完成！")
                    else:
                        st.error(f"❌ 處理失敗：{error}")
                        logger.error(f"處理失敗：{error}")
                except Exception as e:
                    error_msg = f"處理過程發生錯誤: {str(e)}"
                    st.error(f"❌ {error_msg}")
                    logger.error(error_msg)

    # 顯示當前設定
    st.subheader("🔗 API 端點設定")
    st.write("在此設定各個分析功能的 API 端點")

    # 建立設定表單
    with st.form("api_settings"):
        # Langflow 基礎 URL
        base_url = st.text_input(
            "Langflow 基礎 URL",
            value=os.getenv("LANGFLOW_URL", "http://langflow:7860"),
            help="Langflow 服務的基礎 URL"
        )

        # 對話摘要 API
        api_1 = st.text_input(
            "貼文分析 API",
            value=os.getenv("LANGFLOW_API_1", ""),
            help="用於貼文分析的 API 端點"
        )
        # 儲存按鈕
        if st.form_submit_button("💾 儲存設定"):
            try:
                # 讀取現有的 env 檔案內容
                try:
                    with open("env/app.env", "r", encoding="utf-8") as f:
                        env_content = f.read()
                except FileNotFoundError:
                    env_content = ""
                
                # 更新需要修改的設定
                lines = env_content.splitlines()
                new_lines = []
                langflow_url_updated = False
                langflow_api_1_updated = False
                
                for line in lines:
                    if line.startswith("LANGFLOW_URL="):
                        new_lines.append(f'LANGFLOW_URL="{base_url}"')
                        langflow_url_updated = True
                    elif line.startswith("LANGFLOW_API_1="):
                        new_lines.append(f'LANGFLOW_API_1="{api_1}"')
                        langflow_api_1_updated = True
                    else:
                        new_lines.append(line)
                
                if not langflow_url_updated:
                    new_lines.append(f'LANGFLOW_URL="{base_url}"')
                if not langflow_api_1_updated:
                    new_lines.append(f'LANGFLOW_API_1="{api_1}"')
                
                env_content = "\n".join(new_lines)
                # 寫入檔案
                with open("/app/env/app.env", "w", encoding="utf-8") as f:
                    f.write(env_content)
                
                # 重新載入環境變數
                load_dotenv("/app/env/app.env", override=True)
                
                st.success("✅ 設定已成功儲存！")
                st.info("🔄 請重新整理頁面以套用新設定")
            except Exception as e:
                st.error(f"❌ 儲存設定時發生錯誤: {str(e)}")

    # 顯示設定說明
    with st.expander("ℹ️ 設定說明"):
        st.markdown("""
        ### 設定項目說明
        
        1. **Langflow 基礎 URL**
           - Langflow 服務的基本網址
           - 預設值: `http://langflow:7860`
        
        2. **對話摘要 API**
           - 用於分析並摘要對話內容的 API 端點
           - 格式: `[基礎 URL]/api/v1/run/[Flow ID]?stream=false`
        
        3. **意圖分析 API**
           - 用於分析對話意圖的 API 端點
           - 格式: `[基礎 URL]/api/v1/run/[Flow ID]?stream=false`
        
        4. **情緒分析 API**
           - 用於分析對話情緒的 API 端點
           - 格式: `[基礎 URL]/api/v1/run/[Flow ID]?stream=false`
        
        ### 注意事項
        - 修改設定後需要重新整理頁面才會生效
        - 請確保輸入的 API 端點格式正確
        - Flow ID 可以從 Langflow 介面中獲取
        """)

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

            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader(title)
                st.write(content)
                
                if image_list:
                    st.image(image_list, width=300)
            
            with col2:
                result_key = f"analyze_{title}"
                
                # 定義切換函數
                def toggle_analysis(key):
                    if f"show_{key}" not in st.session_state:
                        st.session_state[f"show_{key}"] = True
                    else:
                        st.session_state[f"show_{key}"] = not st.session_state[f"show_{key}"]
                
                # 顯示分析按鈕
                if st.button(
                    "🤖 貼文分析" if not st.session_state.get(f"show_{result_key}", False) else "🤖 隱藏分析",
                    key=f"btn_{result_key}",
                    on_click=toggle_analysis,
                    args=(result_key,),
                    use_container_width=True
                ):
                    pass  # 按鈕點擊事件由 on_click 處理

                # 如果狀態為顯示，則進行分析並顯示結果
                if st.session_state.get(f"show_{result_key}", False):
                    analysis_container = st.container()
                    with analysis_container:
                        if result_key not in st.session_state:
                            with st.spinner("分析中..."):
                                try:
                                    result = analyze_post_content(content)
                                    st.session_state[result_key] = result
                                except Exception as e:
                                    st.error(f"分析失敗: {str(e)}")
                                    st.session_state[f"show_{result_key}"] = False
                                    st.rerun()
                        
                        st.info("AI 分析結果", icon="🤖")
                        st.write(st.session_state[result_key])
            
            st.markdown("---")

# 根據選擇的頁面顯示內容
if st.session_state.active_page == "搜尋":
    search_page()
elif st.session_state.active_page == "分析":
    analyze_page()
else:
    settings_page()
