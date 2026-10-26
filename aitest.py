import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")
API_KEY = os.environ["BAIDU_AI_SEARCH_API_KEY"]

url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"

headers = {
    "Content-Type": "application/json",
    "X-Appbuilder-Authorization": f"Bearer {API_KEY}"
}

payload = {
    "messages": [
        {
            "role": "user",
            "content": "今天热点新闻"
        }
    ],
    "search_source": "baidu_search_v1",
    "search_recency_filter": "week",
    "stream": False,
    "model": "ernie-4.5-turbo-32k",
    "enable_deep_search": False
}

response = requests.post(
    url,
    headers=headers,
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8")
)

response.encoding = "utf-8"
print(response.text)