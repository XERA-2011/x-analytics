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
    """验证 14 大核心指数的配置项完整性"""
    assert len(INDEX_CONFIGS) == 14
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

    assert len(codes) == 14
    # 默认选中 6 大基准 (NDX, SP500, SH000300, HSI, N225, KOSPI)
    assert default_selected_count == 6
    assert "NDX" in codes
    assert "SP500" in codes
    assert "SH000300" in codes
    assert "HSI" in codes
    assert "N225" in codes
    assert "KOSPI" in codes


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
