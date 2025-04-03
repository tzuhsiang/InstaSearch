#!/bin/bash
set -e

# 確保必要目錄存在並具有正確權限
mkdir -p /app/media /app/ig_data /app/logs
chmod -R 777 /app/media /app/ig_data /app/logs

# 運行Streamlit應用
exec streamlit run app.py
