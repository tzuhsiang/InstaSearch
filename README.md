# 📌 InstaSearch - 現代化 AI 全文檢索與分析平台

[![Vue.js](https://img.shields.io/badge/Vue.js-3.0-4FC08D?style=flat&logo=vue.js)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-005571?style=flat&logo=elasticsearch)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com/)

**InstaSearch** 是一個現代化的全端應用程式，結合了 **Elasticsearch** 全文檢索、**FastAPI** 後端服務與 **Vue.js** 高質感前端介面。
本專案提供 Instagram 食記貼文的搜尋與趨勢分析功能，並整合了 **LangGraph** 與 **MCP Server** 架構，內建一個隨時可喚起的 AI Agent 助理。

---

## 🖼️ 介面展示

![Main UI](imgs/demo_ui.png)
*現代化深色模式介面與高效搜尋結果展示*
*主要介面*: [http://localhost:3000](http://localhost:3000)

![AI Agent 測試頁面](imgs/demo_agent.png)
*獨立的 AI Agent 測試頁面，支援 SSE 串流對話與思考過程展示*
*Agent本地測試頁*: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)

---

## 🚀 主要特色

- **🎨 現代化 UI 設計**: 採用 Glassmorphism (玻璃擬態) 風格，提供流暢的搜尋體驗。
- **🔍 強大搜尋引擎**: 基於 Elasticsearch 的高效全文檢索，支援多欄位關鍵字與日期範圍篩選。
- **🤖 內建 AI Agent 側邊欄**:
  - **一鍵喚起**: 在搜尋頁面右上角即可開啟 Agent 側邊欄（寬度佔 1/3）。
  - **動態佈局**: 開啟時主頁面自動縮放，支援一邊搜尋一邊與 AI 對話。
  - **思考透明化**: 支援展示 Agent 的工具呼叫與邏輯推演過程。
- **📊 數據可視化**: 內建移動式圖表，自動分析發文趨勢。
- **🐳 完整容器化**: 使用 Docker Compose 一鍵部署所有服務。

---

## 🛠️ 系統架構

1.  **Frontend**: Vue 3 + Vite + Pinia + Lucide Icons
2.  **Backend**: FastAPI + Python (內植 MCP Server)
3.  **Database**: Elasticsearch
4.  **AI Engine**: LangGraph + Azure OpenAI
5.  **Infrastructure**: Docker Compose

## 📂 專案結構

```bash
InstaSearch/
│── backend/                # FastAPI 後端服務
│   ├── routers/            # API 路由 (search, analysis, settings, chat)
│   ├── agent.py            # LangGraph Agent 核心邏輯
│   └── Dockerfile
│
│── frontend/               # Vue.js 前端應用
│   ├── src/
│   │   ├── components/     # AgentChat, AgentSidebar 等組件
│   │   ├── stores/         # UI 狀態管理 (Pinia)
│   │   ├── views/          # 頁面組件 (Search, Analysis, Settings)
│   │   └── style.css       # 核心設計系統
│   └── Dockerfile
│
│── ig_data/                # 原始資料存放
│── imgs/                   # UI 展示圖檔
│── docker-compose.yml      # 服務編排
└── README.md
```

---

## 🚀 快速開始

### 1️⃣ 前置需求
- 安裝 [Docker](https://www.docker.com/) 與 Docker Compose

### 2️⃣ 啟動服務
```bash
docker-compose up --build
```

服務連結：
- **主要介面**: [http://localhost:3000](http://localhost:3000)
- **API 文件**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Agent 本地測試頁**: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)

---

## 📖 使用指南

### 🔍 搜尋與 AI 助理
- **全文檢索**：支援關鍵字與極速的 Elasticsearch 查詢。
- **喚起助理**：點擊搜尋頁面右上方的 **「AI 助理」** 按鈕，右側會展開對話視窗。
- **邊看邊問**：側邊欄開啟時，主內容會自動調整寬度，讓您可以一邊查看搜尋結果一邊與 AI 對話。

### 📊 趨勢分析
- 切換至「分析」標籤，系統會自動匯總 Elasticsearch 中的數據並生成互動式趨勢圖表。

---

## 🛠️ 常見問題

### Q: 服務啟動後前端顯示 "Network Error"？
**A:** 請確認 `backend` 容器是否成功啟動，且 `.env` (或 `env/app.env`) 中的 Azure OpenAI 設定正確。

### Q: 圖片無法顯示？
**A:** 請確認 `ig_data` 目錄中的圖片路徑與資料庫一致，後端會自動掛載並透過 `/images/` 存取。

### Q: Elasticsearch 回傳 503？
**A:** 這通常是磁碟空間不足導致進入唯讀模式。請解除索引鎖定：
```bash
curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' -d '{"index.blocks.read_only_allow_delete": null}'
```

---

## 📧 聯絡
如有任何問題，歡迎提交 Issue 或 Pull Request。
