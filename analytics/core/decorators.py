"""
API 通用装饰器
提供 safe_endpoint 等简化路由代码的工具
"""

from functools import wraps
from typing import Callable, Dict, Any
from .cache import wrap_response
from .logger import logger


def safe_endpoint(func: Callable) -> Callable:
    """
    统一异常处理装饰器。
    捕获路由函数中的所有异常，返回标准化错误响应。

    Usage:
        @router.get("/some-path")
        @safe_endpoint
        def get_something():
            return SomeModule.calculate()
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API 错误 [{func.__name__}]: {e}")
            return wrap_response(status="error", message=str(e))
    return wrapper


def safe_async_endpoint(func: Callable) -> Callable:
    """
    统一异常处理装饰器 (async 版本)。

    Usage:
        @router.get("/some-path")
        @safe_async_endpoint
        async def get_something():
            return await SomeModule.calculate()
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API 错误 [{func.__name__}]: {e}")
            return wrap_response(status="error", message=str(e))
    return wrapper
