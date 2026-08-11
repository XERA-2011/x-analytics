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

def test_asia_market_routes():
    routes = [
        "/market-asia/indices",
        "/market-asia/fear-greed",
        "/market-asia/bonds/treasury",
        "/market-asia/lpr"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_western_market_routes():
    routes = [
        "/market-western/fear-greed/custom",
        "/market-western/market-heat",
        "/market-western/bond-yields"
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

def test_gold_routes():
    routes = [
        "/gold/spot-prices",
        "/gold/fear-greed",
        "/gold/silver-fear-greed",
        "/gold/central-bank-reserves",
        "/gold/etf-holdings",
        "/gold/gold-silver-ratio",
        "/metals/spot-prices",
        "/metals/fear-greed"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_etf_routes():
    routes = [
        "/etf/heatmap"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_ai_routes():
    routes = [
        "/ai/overview"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503)

def test_index_valuation_routes():
    routes = [
        "/index-valuation/valuation/NDX",
        "/index-valuation/valuation/SP500",
        "/index-valuation/valuation/HSI",
        "/index-valuation/valuation/SH000300",
        "/index-valuation/valuation/CSIH30269",
        "/index-valuation/valuation/SH000015"
    ]
    for route in routes:
        response = requests.get(f"{BASE_URL}{route}")
        assert response.status_code in (200, 503, 202) # support 202/503 for warming up states

