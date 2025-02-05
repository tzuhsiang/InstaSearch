# 使用官方的 Python 基礎映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 安裝 curl（方便除錯）
RUN apt-get update && apt-get install -y curl

# 安裝所需的 Python 套件（不事先 COPY，因為我們用 volumes 掛載）
RUN pip install --no-cache-dir streamlit elasticsearch

# 開放端口 8501 讓 Streamlit 運行
EXPOSE 8501

# 設定執行指令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
