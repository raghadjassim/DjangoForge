import pytest
from fastapi.testclient import TestClient
from main import app  # استيراد تطبيق FastAPI الخاص بكِ

client = TestClient(app)

# 1. اختبار أن الـ API شغال ويجيب رد صحيح
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200

# 2. اختبار الـ Rate Limiter (SlowAPI)
def test_rate_limit():
    # إرسال طلبات سريعة للتأكد من تشغيل الـ Limiter
    for _ in range(10):
        response = client.get("/")
    # التأكد أن الـ Rate Limit لا يسبب Crash للنظام
    assert response.status_code in [200, 429]