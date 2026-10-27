import importlib
import threading
import time

from analytics.core.cache import RedisCache, cached


def test_local_cache_fallback_when_redis_is_unavailable():
    local_cache = RedisCache("redis://127.0.0.1:1/0")

    assert local_cache.set("fallback:key", {"value": 7}, ttl=30)
    assert local_cache.connected is False
    assert local_cache.get("fallback:key") == {"value": 7}

    lock = local_cache.lock("fallback:key")
    assert lock.acquire(blocking=False)
    assert not lock.acquire(blocking=False)
    lock.release()

    assert local_cache.delete_pattern("fallback:*") == 1
    assert local_cache.get("fallback:key") is None


def test_cached_cold_start_is_available_after_local_refresh(monkeypatch):
    local_cache = RedisCache("redis://127.0.0.1:1/0")
    snapshot_saved = threading.Event()
    calls = []

    cache_module = importlib.import_module("analytics.core.cache")
    monkeypatch.setattr(cache_module, "cache", local_cache)
    monkeypatch.setattr("analytics.core.snapshot.load_snapshot", lambda key: None)
    monkeypatch.setattr(
        "analytics.core.snapshot.save_snapshot",
        lambda key, payload: snapshot_saved.set() or True,
    )

    @cached("test:redis-fallback", ttl=30)
    def fetch_data():
        calls.append(1)
        return {"value": "computed"}

    first = fetch_data()
    assert first["status"] == "warming_up"
    assert snapshot_saved.wait(timeout=2)

    second = fetch_data()
    assert second["status"] == "ok"
    assert second["data"] == {"value": "computed"}
    assert len(calls) == 1


def test_local_cache_respects_ttl():
    local_cache = RedisCache("redis://127.0.0.1:1/0")
    assert local_cache.set("fallback:expires", {"value": 1}, ttl=30)
    serialized, _, size = local_cache._local_cache["fallback:expires"]
    local_cache._local_cache["fallback:expires"] = (serialized, time.monotonic() - 1, size)

    assert local_cache.get("fallback:expires") is None
