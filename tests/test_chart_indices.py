import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from analytics.modules.chart.indices_comparison import (
    INDEX_CONFIGS,
    _calc_return_pct,
    fetch_single_index,
    get_indices_comparison,
)


def test_index_configs_structure():
    """验证 15 大核心指数的配置项完整性"""
    assert len(INDEX_CONFIGS) == 15
    codes = set()
    default_selected_count = 0
    for cfg in INDEX_CONFIGS:
        assert "code" in cfg
        assert "name" in cfg
        assert "region" in cfg
        assert "flag" in cfg
        assert "color" in cfg
        assert "default_selected" in cfg
        assert "type" in cfg
        assert "symbol" in cfg
        codes.add(cfg["code"])
        if cfg["default_selected"]:
            default_selected_count += 1

    assert len(codes) == 15
    # 默认选中 6 大基准 (NDX, SP500, SH000300, HSI, N225, KOSPI)
    assert default_selected_count == 6
    assert "NDX" in codes
    assert "SP500" in codes
    assert "SH000300" in codes
    assert "HSI" in codes
    assert "N225" in codes
    assert "KOSPI" in codes
    assert "TWII" in codes

    # 验证中国台湾指数必须以前缀「中国台湾」命名，且为红色系
    tw_cfg = [c for c in INDEX_CONFIGS if c["code"] == "TWII"][0]
    assert tw_cfg["name"].startswith("中国台湾")
    assert tw_cfg["full_name"].startswith("中国台湾")
    assert tw_cfg["color"].upper() in ["#E11D48", "#DE2910", "#EF4444", "#F43F5E", "#DC2626", "#B91C1C", "#BE123C"]


def test_calc_return_pct():
    """测试涨跌幅计算函数"""
    assert _calc_return_pct(110.0, 100.0) == 10.0
    assert _calc_return_pct(90.0, 100.0) == -10.0
    assert _calc_return_pct(100.0, 100.0) == 0.0
    assert _calc_return_pct(100.0, 0.0) is None
    assert _calc_return_pct(100.0, None) is None


@patch("analytics.modules.chart.indices_comparison.akshare_call_with_retry")
def test_fetch_single_index_mock(mock_akshare):
    """测试单个指数数据抓取与收益率计算"""
    dates = [
        "2023-01-01", "2023-06-01", "2023-12-29",
        "2024-01-02", "2024-03-01", "2024-06-01", "2024-08-01", "2024-09-01", "2024-09-25", "2024-10-01"
    ]
    closes = [100.0, 110.0, 120.0, 125.0, 130.0, 140.0, 145.0, 150.0, 155.0, 160.0]
    df = pd.DataFrame({"date": dates, "close": closes})
    mock_akshare.return_value = df

    cfg = INDEX_CONFIGS[0]  # NDX
    res = fetch_single_index(cfg, cutoff_date="2023-01-01")

    assert res is not None
    assert res["code"] == cfg["code"]
    assert res["name"] == cfg["name"]
    assert res["latest_close"] == 160.0
    assert res["latest_date"] == "2024-10-01"
    assert "returns" in res
    # 1D: (160 - 155) / 155 = 3.23%
    assert res["returns"]["1D"] == round((160 - 155) / 155 * 100, 2)
    assert len(res["history"]) == 10


@patch("analytics.modules.chart.indices_comparison.akshare_call_with_retry")
def test_fetch_single_index_filters_zero_prices(mock_akshare):
    """测试自动过滤收盘价为 0 或负数的异常/未收盘数据 (如 KOSPI/SENSEX 异常 0 值)"""
    dates = [
        "2024-09-28", "2024-09-29", "2024-09-30", "2024-10-01", "2024-10-02"
    ]
    # 最后一天 close 为 0.0，中间存在 0.0
    closes = [6889.74, 6870.81, 0.0, 6971.35, 0.0]
    df = pd.DataFrame({"date": dates, "close": closes})
    mock_akshare.return_value = df

    cfg = [c for c in INDEX_CONFIGS if c["code"] == "KOSPI"][0]
    res = fetch_single_index(cfg, cutoff_date="2024-01-01")

    assert res is not None
    # 0.0 被过滤，最新有效收盘应为 2024-10-01 的 6971.35
    assert res["latest_date"] == "2024-10-01"
    assert res["latest_close"] == 6971.35
    assert res["returns"]["1D"] is not None
    assert res["returns"]["1D"] != -100.0
    # 历史记录中不能包含任何 <= 0 的点位
    for h in res["history"]:
        assert h[1] > 0


@patch("analytics.modules.chart.indices_comparison.akshare_call_with_retry")
def test_fetch_taiwan_index(mock_akshare):
    """测试中国台湾加权指数的数据抓取与结构"""
    dates = ["2024-09-28", "2024-09-29", "2024-09-30", "2024-10-01", "2024-10-02"]
    closes = [48000.0, 48100.0, 48200.0, 48300.0, 48400.0]
    df = pd.DataFrame({"date": dates, "close": closes})
    mock_akshare.return_value = df

    cfg = [c for c in INDEX_CONFIGS if c["code"] == "TWII"][0]
    assert cfg["name"].startswith("中国台湾")
    res = fetch_single_index(cfg, cutoff_date="2024-01-01")
    assert res is not None
    assert res["code"] == "TWII"
    assert res["name"] == "中国台湾加权"
    assert res["latest_close"] == 48400.0
    assert res["latest_date"] == "2024-10-02"


from analytics.api.chart import get_global_indices_comparison


def test_api_endpoint_chart_indices():
    """测试 API 路由处理器 get_global_indices_comparison"""
    mock_data = {
        "indices": [
            {
                "code": "NDX",
                "name": "纳指100",
                "region": "US",
                "flag": "🇺🇸",
                "color": "#3B82F6",
                "default_selected": True,
                "latest_date": "2026-10-01",
                "latest_close": 30500.0,
                "history": [["2026-09-01", 30000.0], ["2026-10-01", 30500.0]],
                "returns": {"1D": 0.5, "1W": 1.0, "1M": 2.0, "3M": 3.0, "6M": 5.0, "YTD": 10.0, "1Y": 15.0, "3Y": 30.0}
            }
        ],
        "count": 1,
        "updated_at": "2026-10-02 20:00:00"
    }
    with patch("analytics.api.chart.get_indices_comparison", return_value=mock_data):
        resp = get_global_indices_comparison()
        assert resp["indices"][0]["code"] == "NDX"
        assert resp["count"] == 1
