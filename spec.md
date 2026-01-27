將這個專案進行重新開發

1.使用前後端分離架構，後端使用 FastAPI，前端使用node.js與vue.js
2.使用 Docker Compose 進行部署，包含 Elasticsearch、Postgres、Langflow、Streamlit、Kibana、FastAPI、node.js
3.後端要實作所有功能的API，包含資料的CRUD、貼文分析
4.前端設計分析streamlit目前的頁面，用vue.js重新開發
5.前端側邊欄包含查詢、分析、設定，再新增一個AI Agent頁面，可以透過AI Agent進行查詢
6.使用MCP將Langflow與FastAPI串接起來，讓AI Agent可以透過Langflow進行查詢
