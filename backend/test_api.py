"""
اختبار مباشر للـ API — شغّلي هذا الملف وأرسليلي النتيجة
python test_api.py
"""
import os, json
import httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

print(f"API Key found: {'YES — starts with ' + API_KEY[:15] if API_KEY else 'NO — MISSING!'}")
print(f"Key length: {len(API_KEY)}")

if not API_KEY:
    print("ERROR: Set ANTHROPIC_API_KEY in .env file")
    exit(1)

# اختبار بسيط جداً
body = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 50,
    "system": [
        {
            "type": "text",
            "text": "You are helpful."
        }
    ],
    "messages": [{"role": "user", "content": "Say hello in one word."}]
}

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

print("\nSending test request to Anthropic...")
r = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=30)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")
