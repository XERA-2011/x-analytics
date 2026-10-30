import json
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from analytics.core.security import (
    DISALLOWED_UA_KEYWORDS,
    SecurityMiddleware,
    _is_trusted_domain,
)


def test_is_trusted_domain():
    # 空来源或直接访问（无 Origin / Referer）允许通过
    assert _is_trusted_domain(None) is True
    assert _is_trusted_domain("") is True

    # 信任域名及其子域名
    assert _is_trusted_domain("https://analytics.xerafun.com") is True
    assert _is_trusted_domain("https://xerafun.com") is True
    assert _is_trusted_domain("https://test.xerafun.com/path?q=1") is True
    assert _is_trusted_domain("https://xera.dpdns.org") is True
    assert _is_trusted_domain("https://a1-hy2.xera2011.dpdns.org:443") is True
    assert _is_trusted_domain("https://xera.pages.dev") is True
    assert _is_trusted_domain("https://xerafun.pages.dev") is True
    assert _is_trusted_domain("https://sub.xerafun.pages.dev") is True
    assert _is_trusted_domain("http://localhost:8080") is True
    assert _is_trusted_domain("http://127.0.0.1:8080") is True
    assert _is_trusted_domain("testserver") is True

    # 恶意或伪造域名必须拦截
    assert _is_trusted_domain("https://evil.com") is False
    assert _is_trusted_domain("https://evil-xerafun.com") is False
    assert _is_trusted_domain("https://xerafun.com.attacker.com") is False
    assert _is_trusted_domain("https://dpdns.org.attacker.com") is False
    assert _is_trusted_domain("https://attacker-pages.dev") is False
    assert _is_trusted_domain("null") is False
    assert _is_trusted_domain("javascript:alert(1)") is False


def _build_request(path: str = "/api/test", method: str = "GET", headers: dict = None) -> Request:
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
    }
    return Request(scope)


async def _dummy_next(request: Request):
    return JSONResponse({"status": "ok", "message": "success"})


@pytest.mark.anyio
async def test_trusted_origin_allowed():
    mw = SecurityMiddleware(None)
    req = _build_request("/api/test-data", headers={"Origin": "https://analytics.xerafun.com"})
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_untrusted_origin_rejected():
    mw = SecurityMiddleware(None)
    req = _build_request("/api/test-data", headers={"Origin": "https://evil-hacker.com"})
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 403
    data = json.loads(resp.body.decode("utf-8"))
    assert data["message"] == "Forbidden: untrusted origin"


@pytest.mark.anyio
async def test_trusted_referer_allowed():
    mw = SecurityMiddleware(None)
    req = _build_request("/api/test-data", headers={"Referer": "https://xera.dpdns.org/analytics/"})
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_untrusted_referer_rejected():
    mw = SecurityMiddleware(None)
    req = _build_request("/api/test-data", headers={"Referer": "https://attacker.com/steal"})
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 403
    data = json.loads(resp.body.decode("utf-8"))
    assert data["message"] == "Forbidden: untrusted referer"


@pytest.mark.anyio
async def test_scraper_ua_blocked_on_external_ip():
    mw = SecurityMiddleware(None)
    for ua in ("python-requests/2.32.0", "aiohttp/3.9.5", "python-httpx/0.27.0", "Go-http-client/2.0", "Scrapy/2.11"):
        req = _build_request(
            "/api/test-data",
            headers={"User-Agent": ua, "X-Real-IP": "198.51.100.42"},
        )
        resp = await mw.dispatch(req, _dummy_next)
        assert resp.status_code == 403, f"Expected 403 for UA {ua}"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["message"] == "Forbidden: automated requests disallowed"


@pytest.mark.anyio
async def test_scraper_ua_permitted_on_loopback():
    mw = SecurityMiddleware(None)
    req = _build_request(
        "/api/test-data",
        headers={"User-Agent": "python-requests/2.32.0", "X-Real-IP": "127.0.0.1"},
    )
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_health_check_exempt():
    mw = SecurityMiddleware(None)
    req = _build_request(
        "/api/health",
        headers={"User-Agent": "python-requests/2.32.0", "X-Real-IP": "198.51.100.42"},
    )
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_options_preflight_exempt():
    mw = SecurityMiddleware(None)
    req = _build_request(
        "/api/test-data",
        method="OPTIONS",
        headers={"Origin": "https://evil-hacker.com"},
    )
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_security_headers_added():
    mw = SecurityMiddleware(None)
    req = _build_request(
        "/api/test-data",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "X-Real-IP": "203.0.113.5",
        },
    )
    resp = await mw.dispatch(req, _dummy_next)
    assert resp.status_code == 200
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
