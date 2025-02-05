from elasticsearch import Elasticsearch

# 連接 Elasticsearch（無需帳號密碼）
es = Elasticsearch("http://localhost:9200")

# 測試連線
if es.ping():
    print("✅ 成功連接 Elasticsearch")
else:
    print("❌ 連接失敗")
