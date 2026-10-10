import os
import json
import asyncio
from typing import Optional, Dict, Any
from .logger import logger

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def _sanitize_filename(key: str) -> str:
    """将快照 key 转换为安全的文件名"""
    return key.replace(":", "_").replace("/", "_").replace("\\", "_")


def _save_local_file(key: str, payload: Dict[str, Any]) -> None:
    try:
        filepath = os.path.join(SNAPSHOT_DIR, f"{_sanitize_filename(key)}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[Snapshot] 本地快照文件写入失败 [{key}]: {e}")


def _load_local_file(key: str) -> Optional[Dict[str, Any]]:
    try:
        filepath = os.path.join(SNAPSHOT_DIR, f"{_sanitize_filename(key)}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[Snapshot] 本地快照文件读取失败 [{key}]: {e}")
    return None


async def save_snapshot_async(key: str, payload: Dict[str, Any]) -> bool:
    """异步保存快照至 PostgreSQL 及本地备份文件"""
    _save_local_file(key, payload)
    
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return True

    try:
        from ..models.snapshot import DataSnapshot
        await DataSnapshot.update_or_create(
            key=key,
            defaults={"payload": payload}
        )
        return True
    except Exception as e:
        logger.warning(f"[Snapshot] 数据库快照写入失败 [{key}]: {e}")
        return False


async def load_snapshot_async(key: str) -> Optional[Dict[str, Any]]:
    """异步从 PostgreSQL 加载快照（若失败则回退至本地文件）"""
    from .db import DB_AVAILABLE
    if DB_AVAILABLE:
        try:
            from ..models.snapshot import DataSnapshot
            record = await DataSnapshot.get_or_none(key=key)
            if record and record.payload:
                return record.payload
        except Exception as e:
            logger.warning(f"[Snapshot] 数据库快照读取失败 [{key}]: {e}")

    return _load_local_file(key)


def save_snapshot(key: str, payload: Dict[str, Any]) -> bool:
    """同步保存快照（支持从后台线程、定时任务或同步函数中调用）"""
    _save_local_file(key, payload)

    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return True

    from .scheduler import _main_loop
    if _main_loop is not None and not _main_loop.is_closed():
        try:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is _main_loop:
                _main_loop.create_task(save_snapshot_async(key, payload))
                return True

            future = asyncio.run_coroutine_threadsafe(save_snapshot_async(key, payload), _main_loop)
            return future.result(timeout=10)
        except Exception as e:
            logger.warning(f"[Snapshot] 提交快照写入到主循环失败 [{key}]: {e}")
            return False
    else:
        try:
            return asyncio.run(save_snapshot_async(key, payload))
        except Exception:
            return False


def load_snapshot(key: str) -> Optional[Dict[str, Any]]:
    """同步读取快照（支持从后台线程或同步函数中调用）"""
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return _load_local_file(key)

    from .scheduler import _main_loop
    if _main_loop is not None and not _main_loop.is_closed():
        try:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is _main_loop:
                # 在主循环内部同步调用，直接走本地文件避免自锁
                return _load_local_file(key)

            future = asyncio.run_coroutine_threadsafe(load_snapshot_async(key), _main_loop)
            res = future.result(timeout=5)
            if res is not None:
                return res
        except Exception as e:
            logger.warning(f"[Snapshot] 从主循环读取快照失败 [{key}]: {e}")

    return _load_local_file(key)
