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


def test_proxy_domain_whitelist():
    """验证 Worker 中继代理域名白名单与 SSRF 防护"""
    from analytics.core.utils import _is_allowed_proxy_domain

    # 受信合法白名单
    assert _is_allowed_proxy_domain("https://api.fund.eastmoney.com/f10/lsjz?fundCode=519981")
    assert _is_allowed_proxy_domain("http://fundf10.eastmoney.com/zcpz_519981.html")
    assert _is_allowed_proxy_domain("https://hq.sinajs.cn/list=gb_ixic")
    assert _is_allowed_proxy_domain("https://www.sse.com.cn/market/")

    # 非法或可疑请求 (SSRF / 外部未知域名)
    assert not _is_allowed_proxy_domain("http://127.0.0.1:8080/admin")
    assert not _is_allowed_proxy_domain("http://169.254.169.254/latest/meta-data/")
    assert not _is_allowed_proxy_domain("https://evil-attacker.com/steal")
    assert not _is_allowed_proxy_domain("https://eastmoney.com.evil.com/test")

