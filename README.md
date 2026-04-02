# 📌 InstaSearch - 現代化 AI 全文檢索與分析平台

[![Vue.js](https://img.shields.io/badge/Vue.js-3.0-4FC08D?style=flat&logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-005571?style=flat&logo=elasticsearch)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com/)

**InstaSearch** 是一個現代化的全端應用程式，結合了 **Elasticsearch** 全文檢索、**FastAPI** 後端服務與 **Vue.js** 高質感前端介面。
本專案提供 Instagram 食記貼文的搜尋與趨勢分析功能，並整合了 **LangGraph** 與 **MCP Server** 架構，內建一個能夠自主分析、呼叫查詢工具的強大 AI Agent 助理。

## 🚀 主要特色

- **🎨 現代化 UI 設計**: 採用 Glassmorphism (玻璃擬態) 風格，提供流暢的深色模式體驗。
- **🔍 強大搜尋引擎**: 基於 Elasticsearch 的高效全文檢索，支援關鍵字與日期範圍篩選。
- **📊 數據可視化**: 內建互動式圖表，自動分析發文趨勢。
- **🤖 AI Agent 助理**:
  - **多智能體協作**: 整合 LangGraph，由 `Supervisor`、`Retriever` 等不同角色的 AI 工具組建而成的多代理架構。
  - **MCP 協議支援**: 後端內建 `instagram` (資料庫查詢) 與 `system_api` (趨勢查詢) 等基礎設施等級的延伸工具。
  - **即時串流對話**: 提供獨立的 Agent 測試頁面與完善的 Vue 前端聊天介面，支援思考過程 (Reasoning) 可視化。
- **🐳 完整容器化**: 使用 Docker Compose 一鍵部署所有服務 (Frontend, Backend, DB, AI Engine)。

---

## 🛠️ 系統架構

本專案採用前後端分離架構：

1.  **Frontend**: Vue 3 + Vite + Tailwind/Vanilla CSS 
2.  **Backend**: FastAPI + Python (內植 MCP Server)
3.  **Database**: Elasticsearch (搜尋引擎與原始資料庫)
4.  **AI Engine**: LangGraph (LLM 邏輯與多代理人編排)
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
- **Standalone Agent UI**: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) (Agent 獨立測試頁)
- **Kibana**: [http://localhost:5601](http://localhost:5601) (資料儀表板)
- **Elasticsearch**: [http://localhost:9200](http://localhost:9200)

### 3️⃣ 資料匯入
若您有 Instagram 備份資料 (ZIP 格式)，請將其放入 `ig_data/` 目錄。
後端服務啟動時會自動掛載此目錄，您可透過相關腳本 (如 `setup.py` 或 API) 來觸發資料匯入 (需視具體實作而定)。

---

## 📖 使用指南

### 🔍 搜尋頁面
- **自動搜尋**：進入頁面時，系統會自動載入最近 **兩年** 的資料。
- 支援輸入關鍵字自訂搜尋範圍。
- 支援查看貼文內容、分數 (Score) 與圖片預覽。

### 📊 分析頁面
- 自動讀取 Elasticsearch 數據，展示每月的發文數量趨勢圖。

### 💬 AI Agent
- 獨立的助理對話功能！具備基於 LangGraph 打造的分析助理。
- Agent 可以自動分析您的提問，並且自主呼叫對應的 MCP Tool (例如 `search_instagram` 來獲得第一手貼文資料)。
- 推薦使用 [Agent 獨立測試頁](http://localhost:8000/static/index.html) 獲得完整的分析過程與思考步驟。

### ⚙️ 系統設定
- 將 Azure OpenAI 的 金鑰與 Endpoint 加入至 `env/app.env`：
  ```env
  AZURE_OPENAI_API_KEY="..."
  AZURE_OPENAI_ENDPOINT="..."
  AZURE_DEPLOYMENT_NAME="..."
  ```
- 修改後請重啟 `backend` 容器。

---

## 🛠️ 常見問題

### Q: 服務啟動後前端顯示 "Network Error"？
**A:** 
1. 請確認後端容器 (`backend`) 是否已成功啟動且無錯誤。
2. 檢查 API 呼叫是否包含結尾斜線（FastAPI Redirect 機制可能導致 Docker 內部 IP 暴露問題），例如應使用 `/api/search/` 而非 `/api/search`。

### Q: Elasticsearch 回傳 503 或 "Cluster Block Exception"？
**A:** 這通常是因為 Docker Host 磁碟空間不足（>95% 使用率），導致 Elasticsearch 觸發 Flood Stage Protection 並強制鎖定為唯讀。
**解決方案**：
1. 清理 Docker 暫存：`docker system prune -a`
2. 解除索引鎖定：
   ```bash
   curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' -d '{"index.blocks.read_only_allow_delete": null}'
   ```

### Q: Backend 報錯 "Elasticsearch client version incompatibility"？
**A:** 專案已鎖定 `elasticsearch<9.0.0` 以相容 v8 伺服器。若自行重建環境，請確保不要安裝 v9 以上的 Python client。


### Q: 圖片無法顯示？
**A:** 請確認 `ig_data` 或 `media` 資料夾權限正確，且圖片路徑與資料庫中的 `uri` 欄位一致。後端已設定靜態檔案掛載，可直接透過 `/images/...` 存取。

---

## 📧 聯絡
如有任何問題，歡迎提交 Issue 或 Pull Request。
