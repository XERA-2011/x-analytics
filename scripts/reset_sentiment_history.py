#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
重建 SentimentHistory 数据表脚本
当升级代码添加了新的列（如 indicator_type）导致线上数据库报错时，
可以使用此脚本将旧表丢弃并重新生成。
警告：此操作会清空所有的历史情绪指标快照数据！
"""

import asyncio
import os
import sys

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from tortoise import Tortoise

async def main():
    print("⚠️ 警告：这将删除 sentiment_history 表的所有数据！")
    confirm = input("确定要继续吗？(y/N): ")
    if confirm.lower() != 'y':
        print("操作已取消。")
        return

    # 加载环境变量
    load_dotenv(".env.local")
    
    from analytics.core.db import TORTOISE_ORM
    
    print("🔄 正在连接数据库...")
    await Tortoise.init(config=TORTOISE_ORM)
    
    conn = Tortoise.get_connection("default")
    
    print("🗑️ 正在删除旧表 sentiment_history...")
    await conn.execute_script("DROP TABLE IF EXISTS sentiment_history;")
    
    print("🏗️ 正在重新生成 Schema...")
    await Tortoise.generate_schemas()
    
    print("✅ Schema 重建完成，新的 sentiment_history 表已就绪！")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
