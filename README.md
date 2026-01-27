# 📌 InstaSearch - 現代化 AI 全文檢索與分析平台

[![Vue.js](https://img.shields.io/badge/Vue.js-3.0-4FC08D?style=flat&logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-005571?style=flat&logo=elasticsearch)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com/)

**InstaSearch** 是一個現代化的全端應用程式，結合了 **Elasticsearch** 全文檢索、**FastAPI** 後端服務與 **Vue.js** 高質感前端介面。
本專案不僅提供 Instagram 貼文的搜尋功能，更整合了 **Langflow** 與 **MCP Server** 架構，支援 AI 貼文分析與智慧對話代理 (AI Agent)。

## 🚀 主要特色

- **🎨 現代化 UI 設計**: 採用 Glassmorphism (玻璃擬態) 風格，提供流暢的深色模式體驗。
- **🔍 強大搜尋引擎**: 基於 Elasticsearch 的高效全文檢索，支援關鍵字與日期範圍篩選。
- **📊 數據可視化**: 內建互動式圖表，自動分析發文趨勢。
- **🤖 AI 智能分析**:
  - **貼文分析**: 整合 Langflow，可針對單篇貼文進行深度內容分析。
  - **AI Agent**: 內建聊天室介面，支援透過 MCP 協議與後端 AI Agent 互動 (需自行配置 Langflow Agent)。
- **🐳 完整容器化**: 使用 Docker Compose 一鍵部署所有服務 (Frontend, Backend, DB, AI Engine)。

---

## 🛠️ 系統架構

本專案採用前後端分離架構：

1.  **Frontend**: Vue 3 + Vite + Vanilla CSS (Glassmorphism)
2.  **Backend**: FastAPI + Python
3.  **Database**: Elasticsearch (搜尋引擎) + PostgreSQL (Langflow 資料庫)
4.  **AI Engine**: Langflow (LLM 流程編排)
5.  **Infrastructure**: Docker Compose

## 📂 專案結構

```bash
InstaSearch/
│── backend/                # [NEW] FastAPI 後端服務
│   ├── main.py             # 應用程式入口
│   ├── routers/            # API 路由 (search, analysis, settings, mcp)
│   ├── database.py         # DB 連線邏輯
│   └── Dockerfile
│
│── frontend/               # [NEW] Vue.js 前端應用
│   ├── src/
│   │   ├── views/          # 頁面組件 (Search, Analysis, Agent...)
│   │   ├── components/     # 共用組件
│   │   └── style.css       # 全域樣式設定
│   └── Dockerfile
│
│── data/                   # Elasticsearch 資料持久化目錄
│── ig_data/                # Instagram 匯入的原始資料
│── media/                  # 媒體檔案目錄
│── langflow-data/          # Langflow 設定檔
│── docker-compose.yml      # 服務編排設定
└── spec.md                 # 開發規格書
```

---

## 🚀 快速開始

### 1️⃣ 前置需求
- 安裝 [Docker](https://www.docker.com/) 與 Docker Compose

### 2️⃣ 啟動服務
在專案根目錄下執行：

```bash
docker-compose up --build
```

系統將自動啟動以下服務：
- **Frontend**: [http://localhost:3000](http://localhost:3000) (主要操作介面)
- **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Langflow**: [http://localhost:7860](http://localhost:7860) (AI 流程編排)
- **Kibana**: [http://localhost:5601](http://localhost:5601) (資料儀表板)
- **Elasticsearch**: [http://localhost:9200](http://localhost:9200)

### 3️⃣ 資料匯入
若您有 Instagram 備份資料 (ZIP 格式)，請將其放入 `ig_data/` 目錄。
後端服務啟動時會自動掛載此目錄，您可透過相關腳本 (如 `setup.py` 或 API) 來觸發資料匯入 (需視具體實作而定)。

---

## 📖 使用指南

### 🔍 搜尋頁面
- 輸入關鍵字或選擇日期範圍進行搜尋。
- 支援查看貼文內容、分數 (Score) 與圖片預覽。
- 點擊卡片上的「🤖 貼文分析」按鈕，即可呼叫後端 AI 進行內容解析 (需先在設定頁面配置 API)。

### 📊 分析頁面
- 自動讀取 Elasticsearch 數據，展示每月的發文數量趨勢圖。

### 💬 AI Agent
- 提供一個聊天介面，預設整合 MCP Server 協議。
- 需在 Langflow 中建立對應的 Agent Flow，並確保後端已正確連線。

### ⚙️ 系統設置
- 設定 Langflow 的 Base URL 與相關 API Endpoint。
- 設定將儲存於 `env/app.env`，並熱重載後端環境變數。

---

## 🛠️ 常見問題

### Q: 服務啟動後前端顯示 "Network Error"？
**A:** 請確認後端容器 (`backend`) 是否已成功啟動且無錯誤。前端預設透過 Proxy `/api` 連線至後端，請確保 Docker Network 設定正確。

### Q: 如何設定 AI 分析功能？
**A:**
1. 進入 Langflow ([http://localhost:7860](http://localhost:7860)) 建立 Flow。
2. 取得 Flow 的 API Endpoint。
3. 在 InstaSearch 前端的「系統設置」頁面填入該 API URL。

### Q: 圖片無法顯示？
**A:** 請確認 `ig_data` 或 `media` 資料夾權限正確，且圖片路徑與資料庫中的 `uri` 欄位一致。後端已設定靜態檔案掛載，可直接透過 `/images/...` 存取。

---

## 📧 聯絡
如有任何問題，歡迎提交 Issue 或 Pull Request。
