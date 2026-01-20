#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
智能调度器模块
基于交易时间的智能缓存预热调度
"""

from datetime import date
from typing import Callable, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from functools import lru_cache
import akshare as ak
from .config import settings
from .utils import get_refresh_interval, get_beijing_time


class SmartScheduler:
    """智能调度器 - 基于交易时间的缓存预热"""

    _instance: Optional["SmartScheduler"] = None

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,  # 合并错过的任务
                "max_instances": 1,  # 同一任务最多一个实例
                "misfire_grace_time": 60,  # 错过任务的容忍时间
            },
        )
        self._jobs: List[str] = []
        self._started = False

    @classmethod
    def get_instance(cls) -> "SmartScheduler":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_market_job(
        self,
        job_id: str,
        func: Callable,
        market: str,
        cache_type: str = "default",
        **kwargs,
    ):
        """
        添加市场相关的预热任务

        Args:
            job_id: 任务 ID
            func: 预热函数
            market: 市场类型 ('cn_market', 'us_market', 'metals')
            cache_type: 缓存类型，用于确定TTL
            **kwargs: 传递给 func 的参数
        """

        def smart_warmup():
            """智能预热函数"""
            try:
                # 获取当前刷新间隔
                interval = get_refresh_interval(market)

                # 检查是否应该执行
                now = get_beijing_time()
                minute = now.minute

                # 根据间隔决定是否执行
                if interval >= 3600:  # 1小时以上
                    # 只在整点执行
                    if minute == 0:
                        func(**kwargs)
                elif interval >= 1800:  # 30分钟以上
                    # 在 0, 30 分执行
                    if minute % 30 == 0:
                        func(**kwargs)
                elif interval >= 300:  # 5分钟以上
                    # 在 0, 5, 10... 分执行
                    if minute % 5 == 0:
                        func(**kwargs)
                else:
                    # 高频执行
                    func(**kwargs)

            except Exception as e:
                print(f"❌ 预热任务失败 [{job_id}]: {e}")

        # 使用最小间隔注册任务，在函数内部进行智能过滤
        min_interval = min(
            settings.REFRESH_INTERVALS["trading_hours"].get(market, 300),
            settings.REFRESH_INTERVALS["non_trading_hours"].get(market, 1800),
        )

        # 转换为分钟，最小1分钟
        interval_minutes = max(1, min_interval // 60)

        self.scheduler.add_job(
            smart_warmup,
            IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True,
        )
        self._jobs.append(job_id)
        print(f"✅ 注册智能预热任务: {job_id} (市场: {market})")

    def add_simple_job(
        self, job_id: str, func: Callable, interval_minutes: int = 5, **kwargs
    ):
        """
        添加简单间隔任务

        Args:
            job_id: 任务 ID
            func: 执行函数
            interval_minutes: 执行间隔（分钟）
            **kwargs: 传递给 func 的参数
        """

        def job_wrapper():
            try:
                func(**kwargs)
            except Exception as e:
                print(f"❌ 任务失败 [{job_id}]: {e}")

        self.scheduler.add_job(
            job_wrapper,
            IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True,
        )
        self._jobs.append(job_id)
        print(f"✅ 注册任务: {job_id} (间隔: {interval_minutes}分钟)")

    def add_cron_job(self, job_id: str, func: Callable, cron_expr: str, **kwargs):
        """
        添加定时任务

        Args:
            job_id: 任务 ID
            func: 执行函数
            cron_expr: Cron表达式 (如 "0 9 * * 1-5" 表示工作日9点)
            **kwargs: 传递给 func 的参数
        """

        def job_wrapper():
            try:
                func(**kwargs)
            except Exception as e:
                print(f"❌ 定时任务失败 [{job_id}]: {e}")

        # 解析cron表达式
        parts = cron_expr.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts

            self.scheduler.add_job(
                job_wrapper,
                CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                ),
                id=job_id,
                replace_existing=True,
            )
            self._jobs.append(job_id)
            print(f"✅ 注册定时任务: {job_id} ({cron_expr})")

    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            print("🚀 智能调度器已启动")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            print("🛑 智能调度器已关闭")

    def get_status(self) -> dict:
        """获取调度器状态"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append(
                {
                    "id": job.id,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )

        return {
            "running": self._started,
            "job_count": len(jobs_info),
            "jobs": jobs_info,
        }

    def run_job_now(self, job_id: str) -> bool:
        """立即执行指定任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            try:
                job.func()
                return True
            except Exception as e:
                print(f"❌ 手动执行任务失败 [{job_id}]: {e}")
        return False


# 全局调度器实例
scheduler = SmartScheduler.get_instance()


@lru_cache(maxsize=1)
def _get_trading_days_cache(year: int) -> set:
    """获取指定年份的交易日历（缓存）"""
    try:
        print(f"📅正在获取 {year} 年交易日历...")
        tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
        df = tool_trade_date_hist_sina_df
        trade_dates = set(df["trade_date"].dt.strftime("%Y-%m-%d").tolist())
        return trade_dates
    except Exception as e:
        print(f"⚠️ 获取交易日历失败: {e}")
        return set()


def is_trading_day(d: Optional[date] = None) -> bool:
    """判断是否是交易日"""
    if d is None:
        d = date.today()

    # 1. 基础过滤：周末
    if d.weekday() >= 5:
        return False

    # 2. 精确过滤：查表（处理法定节假日）
    try:
        trading_days = _get_trading_days_cache(d.year)
        if trading_days:
            return d.strftime("%Y-%m-%d") in trading_days
    except Exception:
        pass

    # 降级策略：默认周一到周五都是
    return True


def setup_default_jobs():
    """设置默认的预热任务"""

    print("🔧 设置默认预热任务...")

    # 开盘前预热任务 (工作日 9:25)
    def pre_market_warmup():
        if is_trading_day():
            print("🌅 执行开盘前预热...")
            initial_warmup()

    scheduler.add_cron_job(
        job_id="warmup:pre_market",
        func=pre_market_warmup,
        cron_expr="25 9 * * 1-5",  # 工作日9:25
    )


def warmup_with_retry(func, name: str, max_retries: int = 3, *args, **kwargs) -> bool:
    """带重试的缓存预热"""
    import time
    from .cache import warmup_cache

    for attempt in range(max_retries):
        try:
            warmup_cache(func, *args, **kwargs)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # 指数退避
                print(f"  ⚠️ {name}预热失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print(f"     {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ {name}预热失败 (已重试{max_retries}次): {e}")
                return False
    return False


def initial_warmup():
    """启动时立即执行一次预热"""
    print("🔥 开始初始缓存预热...")
    # 这里会在后续步骤中添加具体的预热逻辑
    print("🔥 初始缓存预热完成")
