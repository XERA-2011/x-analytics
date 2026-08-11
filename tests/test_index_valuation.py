import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date
import numpy as np

# Import functions to test
from analytics.modules.index_valuation import get_index_valuation, INDEX_MAPPING

def test_unsupported_index():
    func_to_run = get_index_valuation._original if hasattr(get_index_valuation, "_original") else get_index_valuation
    with pytest.raises(ValueError) as excinfo:
        func_to_run("INVALID_INDEX")
    assert "Unsupported index code" in str(excinfo.value)


@patch("analytics.modules.index_valuation.requests.get")
@patch("analytics.modules.index_valuation.akshare_call_with_retry")
@patch("analytics.modules.index_valuation.cached")
def test_get_index_valuation_sh000300(mock_cached, mock_akshare_call, mock_get):
    # Mock cached decorator to simply execute the function
    mock_cached.side_effect = lambda *args, **kwargs: lambda func: func
    
    # 1. Mock Danjuan PE history response
    mock_pe_resp = MagicMock()
    mock_pe_resp.json.return_value = {
        "data": {
            "index_eva_pe_growths": [
                {"pe": 10.0, "ts": 1609459200000},  # 2021-01-01
                {"pe": 11.0, "ts": 1609545600000},  # 2021-01-02
                {"pe": 12.0, "ts": 1609632000000},  # 2021-01-03
                {"pe": 13.0, "ts": 1609718400000},  # 2021-01-04
                {"pe": 9.0,  "ts": 1609804800000}   # 2021-01-05
            ]
        }
    }
    mock_pe_resp.status_code = 200
    
    # 2. Mock Sina KLine price response
    mock_price_resp = MagicMock()
    mock_price_resp.json.return_value = [
        {"day": "2021-01-01 15:00:00", "close": "4000.0"},
        {"day": "2021-01-02 15:00:00", "close": "4100.0"},
        {"day": "2021-01-03 15:00:00", "close": "4200.0"},
        {"day": "2021-01-04 15:00:00", "close": "4300.0"},
        {"day": "2021-01-05 15:00:00", "close": "3900.0"}
    ]
    mock_price_resp.status_code = 200
    
    # Side effects for mock_get
    mock_get.side_effect = [mock_pe_resp, mock_price_resp]
    
    # Run the function (caching decorator bypassed via mock)
    # We must call the original function, but since it's decorated we can call its _original
    func_to_run = get_index_valuation._original if hasattr(get_index_valuation, "_original") else get_index_valuation
    res = func_to_run("SH000300")
    
    # Asserts
    assert res["name"] == "沪深300"
    assert res["index_code"] == "SH000300"
    assert res["current_pe"] == 9.0
    assert res["data_date"] == "2021-01-05"
    assert res["eval_level"] in ("low", "medium", "high")
    
    # Sorted PE list: [9.0, 10.0, 11.0, 12.0, 13.0]
    # latest_pe = 9.0, number of values <= 9.0 is 1. total is 5.
    # percentile = 1/5 = 0.2
    assert res["percentile"] == 0.2
    assert res["eval_level"] == "medium"  # percentile < 0.2 is low, percentile < 0.8 is medium, else high
    
    # Percentiles:
    # np.percentile([9.0, 10.0, 11.0, 12.0, 13.0], [20, 50, 80])
    # 20%: 9.8, 50%: 11.0, 80%: 12.2
    assert res["percentile_lines"]["p20"] == 9.8
    assert res["percentile_lines"]["p50"] == 11.0
    assert res["percentile_lines"]["p80"] == 12.2
    
    assert len(res["pe_series"]) == 5
    assert res["pe_series"][0] == ["2021-01-01", 10.0]
    assert res["pe_series"][-1] == ["2021-01-05", 9.0]
    
    assert len(res["price_series"]) == 5
    assert res["price_series"][0] == ["2021-01-01", 4000.0]
    assert res["price_series"][-1] == ["2021-01-05", 3900.0]


@patch("analytics.modules.index_valuation.requests.get")
@patch("analytics.modules.index_valuation.akshare_call_with_retry")
def test_get_index_valuation_hsi(mock_akshare_call, mock_get):
    # 1. Mock Danjuan PE history response
    mock_pe_resp = MagicMock()
    mock_pe_resp.json.return_value = {
        "data": {
            "index_eva_pe_growths": [
                {"pe": 30.0, "ts": 1609459200000},  # 2021-01-01
                {"pe": 32.0, "ts": 1609545600000},  # 2021-01-02
                {"pe": 28.0, "ts": 1609632000000}   # 2021-01-03
            ]
        }
    }
    mock_pe_resp.status_code = 200
    mock_get.return_value = mock_pe_resp
    
    # 2. Mock AkShare response for HSI
    mock_df = pd.DataFrame({
        "date": [date(2021, 1, 1), date(2021, 1, 2), date(2021, 1, 3)],
        "close": [6000.0, 6100.0, 5900.0]
    })
    mock_akshare_call.return_value = mock_df
    
    func_to_run = get_index_valuation._original if hasattr(get_index_valuation, "_original") else get_index_valuation
    res = func_to_run("HSI")
    
    assert res["name"] == "恒生指数"
    assert res["index_code"] == "HSI"
    assert res["current_pe"] == 28.0
    assert res["data_date"] == "2021-01-03"
    
    # Sorted PE: [28.0, 30.0, 32.0]
    # latest: 28.0. <= 28.0 is 1. total 3.
    # percentile = 1/3 = 0.3333
    assert res["percentile"] == round(1/3, 4)
    assert res["eval_level"] == "medium"
    
    assert len(res["price_series"]) == 3
    assert res["price_series"][0] == ["2021-01-01", 6000.0]
    assert res["price_series"][-1] == ["2021-01-03", 5900.0]


@patch("analytics.modules.index_valuation.requests.get")
@patch("analytics.modules.index_valuation.akshare_call_with_retry")
@patch("analytics.modules.index_valuation.cached")
def test_get_index_valuation_csih30269_proxy(mock_cached, mock_akshare_call, mock_get):
    mock_cached.side_effect = lambda *args, **kwargs: lambda func: func
    
    # 1. Mock Danjuan PE history response
    mock_pe_resp = MagicMock()
    mock_pe_resp.json.return_value = {
        "data": {
            "index_eva_pe_growths": [
                {"pe": 7.0, "ts": 1609459200000}
            ]
        }
    }
    mock_pe_resp.status_code = 200
    
    # 2. Mock Sina KLine price response (ETF price around 1.1)
    mock_price_resp = MagicMock()
    mock_price_resp.json.return_value = [
        {"day": "2021-01-01 15:00:00", "close": "1.163"}
    ]
    mock_price_resp.status_code = 200
    
    mock_get.side_effect = [mock_pe_resp, mock_price_resp]
    
    func_to_run = get_index_valuation._original if hasattr(get_index_valuation, "_original") else get_index_valuation
    res = func_to_run("CSIH30269")
    
    assert res["name"] == "红利低波"
    assert res["index_code"] == "CSIH30269"
    # ETF close of 1.163 should be scaled by 10000 to become 11630.0
    assert res["price_series"][0] == ["2021-01-01", 11630.0]
