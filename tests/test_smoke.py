import os
import requests
import pytest

# 默认使用本地 8080 端口，可通过环境变量覆盖，方便在 CI/CD 或 x-actions 中配置
BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8080")

def test_health_check():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "data_source" in data

def test_cn_market_routes():
    routes = [
        "/market-cn/indices",
        "/market-cn/fear-greed",
        "/market-cn/sectors/all",
        "/market-cn/bonds/treasury",
        "/market-cn/lpr"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_us_market_routes():
    routes = [
        "/market-us/fear-greed/custom",
        "/market-us/market-heat",
        "/market-us/bond-yields"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_hk_market_routes():
    routes = [
        "/market-hk/indices",
        "/market-hk/fear-greed"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_metals_routes():
    routes = [
        "/metals/spot-prices",
        "/metals/fear-greed",
        "/metals/silver-fear-greed"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)
