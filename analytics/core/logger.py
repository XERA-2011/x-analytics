"""
统一日志配置
使用 loguru 提供结构化日志
"""

import sys
from loguru import logger

# 移除默认 handler
logger.remove()

# 添加控制台 handler (带颜色)
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 导出 logger 实例供其他模块使用
__all__ = ["logger"]
