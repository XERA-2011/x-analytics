import pytest
from analytics.core.security import PUBLIC_API_PATHS, _is_api_path
from analytics.core.snapshot import save_snapshot, load_snapshot, _save_local_file, _load_local_file


def test_security_whitelist():
    """验证 /chart/ 和 /index-valuation/ 已正确加入 API 白名单"""
    assert "/chart/" in PUBLIC_API_PATHS
    assert "/index-valuation/" in PUBLIC_API_PATHS
    assert "/gold/" in PUBLIC_API_PATHS
    assert _is_api_path("/chart/indices-comparison")
    assert _is_api_path("/index-valuation/valuation/NDX")
    assert _is_api_path("/analytics/chart/indices-comparison")


def test_snapshot_local_persistence():
    """验证快照存储与读取能力"""
    test_key = "test:unit:chart_comparison"
    test_payload = {"status": "ok", "indices": [{"code": "TEST", "name": "测试指数"}]}

    # 测试本地文件存取
    _save_local_file(test_key, test_payload)
    loaded = _load_local_file(test_key)
    assert loaded is not None
    assert loaded["status"] == "ok"
    assert loaded["indices"][0]["code"] == "TEST"

    # 测试同步门面
    save_snapshot(test_key, test_payload)
    res = load_snapshot(test_key)
    assert res is not None
    assert res["status"] == "ok"
