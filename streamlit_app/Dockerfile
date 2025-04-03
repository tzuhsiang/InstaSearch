FROM python:3.9-slim

WORKDIR /app

# 設置大檔案上傳限制
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=500

# 首先複製requirements.txt
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 創建必要的目錄並設置權限
RUN mkdir -p /app/media /app/ig_data /app/logs && \
    chmod -R 777 /app

# 複製應用程式檔案
COPY . .

# 確保所有檔案都有適當的權限
RUN chmod -R 777 /app && \
    chmod +x /app/entrypoint.sh

# 運行應用程式
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
