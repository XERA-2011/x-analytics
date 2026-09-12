import pytest
from analytics.modules.qdii import QDII_FUND_METADATA

def test_qdii_metadata_519981():
    item = next((f for f in QDII_FUND_METADATA if f["code"] == "519981"), None)
    assert item is not None, "519981 not found in QDII_FUND_METADATA"
    assert item["name"] == "长信标普100等权重指数(QDII)A"
    assert item["index_code"] == "SPX_100"
    assert item["index_name"] == "标普100"
    assert item["fee_rate"] == "1.30%"
    assert item["tag"] == "标普100"
    assert "stock_us_pct" in item["default_asset_allocation"]
    assert item["default_asset_allocation"]["stock_pct"] == 85.54

def test_all_qdii_metadata_structure():
    required_keys = [
        "code", "name", "index_code", "index_name",
        "fee_rate", "tracking_error", "inception_date",
        "default_return_1y", "default_nav", "default_nav_date",
        "default_asset_allocation"
    ]
    seen_codes = set()
    for item in QDII_FUND_METADATA:
        code = item.get("code")
        assert code not in seen_codes, f"Duplicate fund code {code}"
        seen_codes.add(code)
        for k in required_keys:
            assert k in item, f"Missing key '{k}' in fund {code}"
        assert isinstance(item["default_asset_allocation"], dict)
        assert "stock_pct" in item["default_asset_allocation"]
