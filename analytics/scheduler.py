#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
后台调度器模块
使用 APScheduler 定时预热缓存
"""

import os
from datetime import datetime
from typing import Callable, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


class CacheScheduler:
    """缓存预热调度器"""
    
    _instance: Optional['CacheScheduler'] = None
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 同一任务最多一个实例
                'misfire_grace_time': 60,  # 错过任务的容忍时间
            }
        )
        self._jobs: List[str] = []
        self._started = False
    
    @classmethod
    def get_instance(cls) -> 'CacheScheduler':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_warmup_job(
        self,
        job_id: str,
        func: Callable,
        trading_interval_minutes: int = 1,
        non_trading_interval_minutes: int = 30,
        **kwargs
    ):
        """
        添加预热任务（交易时段感知）
        
        Args:
            job_id: 任务 ID
            func: 预热函数
            trading_interval_minutes: 交易时段刷新间隔（分钟）
            non_trading_interval_minutes: 非交易时段刷新间隔（分钟）
            **kwargs: 传递给 func 的参数
        """
        # 包装函数，添加时间感知
        def smart_warmup():
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            weekday = now.weekday()  # 0=周一, 6=周日
            
            # 判断是否在交易时段（周一到周五 9:30-15:00）
            is_trading_hours = (
                weekday < 5 and  # 周一到周五
                ((hour == 9 and minute >= 30) or (10 <= hour < 15) or (hour == 15 and minute == 0))
            )
            
            # 非交易时段，根据间隔决定是否执行
            if not is_trading_hours:
                # 每 N 分钟执行一次（通过检查当前分钟是否能被间隔整除）
                if minute % non_trading_interval_minutes != 0:
                    return  # 跳过本次执行
            
            try:
                print(f"🔄 执行预热任务: {job_id}")
                func(**kwargs)
            except Exception as e:
                print(f"❌ 预热任务失败 [{job_id}]: {e}")
        
        # 使用较短的间隔注册任务（交易时段间隔）
        # 非交易时段的频率控制在 smart_warmup 内部实现
        self.scheduler.add_job(
            smart_warmup,
            IntervalTrigger(minutes=trading_interval_minutes),
            id=job_id,
            replace_existing=True
        )
        self._jobs.append(job_id)
        print(f"✅ 注册预热任务: {job_id} (交易时段: {trading_interval_minutes}分钟, 其他: {non_trading_interval_minutes}分钟)")
    
    def add_simple_job(
        self,
        job_id: str,
        func: Callable,
        interval_minutes: int = 5,
        **kwargs
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
                print(f"🔄 执行任务: {job_id}")
                func(**kwargs)
            except Exception as e:
                print(f"❌ 任务失败 [{job_id}]: {e}")
        
        self.scheduler.add_job(
            job_wrapper,
            IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True
        )
        self._jobs.append(job_id)
        print(f"✅ 注册任务: {job_id} (间隔: {interval_minutes}分钟)")
    
    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            print("🚀 缓存调度器已启动")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            print("🛑 缓存调度器已关闭")
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        
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
scheduler = CacheScheduler.get_instance()


def setup_default_warmup_jobs():
    """
    设置默认的缓存预热任务
    
    在 server.py 启动时调用
    """
    from .cache import warmup_cache
    from .market import MarketAnalysis
    from .sentiment import SentimentAnalysis
    
    # 市场概览 - 热点数据，高频刷新
    scheduler.add_warmup_job(
        job_id="warmup:market:overview",
        func=lambda: warmup_cache(MarketAnalysis.get_market_overview_v2),
        trading_interval_minutes=1,
        non_trading_interval_minutes=30,
    )
    
    # 恐慌贪婪指数 - 计算较重，低频刷新
    # 注意：必须传递与 API 默认值一致的参数，确保缓存键匹配
    scheduler.add_warmup_job(
        job_id="warmup:sentiment:fear_greed",
        func=lambda: warmup_cache(SentimentAnalysis.calculate_fear_greed_custom, symbol="sh000001", days=14),
        trading_interval_minutes=5,
        non_trading_interval_minutes=60,
    )
    
    # 板块排行
    scheduler.add_warmup_job(
        job_id="warmup:market:sector_top",
        func=lambda: warmup_cache(MarketAnalysis.get_sector_top),
        trading_interval_minutes=3,
        non_trading_interval_minutes=60,
    )
    
    scheduler.add_warmup_job(
        job_id="warmup:market:sector_bottom",
        func=lambda: warmup_cache(MarketAnalysis.get_sector_bottom),
        trading_interval_minutes=3,
        non_trading_interval_minutes=60,
    )

    # -------------------------------------------------------------------------
    # 新增预热任务
    # -------------------------------------------------------------------------
    from .index import IndexAnalysis
    from .fund import FundAnalysis

    # 主要指数对比
    scheduler.add_warmup_job(
        job_id="warmup:index:compare",
        func=lambda: warmup_cache(IndexAnalysis.compare_indices),
        trading_interval_minutes=1,
        non_trading_interval_minutes=30,
    )

    # 基金排行 (低频更新)
    scheduler.add_warmup_job(
        job_id="warmup:fund:top",
        func=lambda: warmup_cache(FundAnalysis.get_top_funds, indicator="近1年", top_n=10),
        trading_interval_minutes=60,
        non_trading_interval_minutes=240,
    )


def initial_warmup():
    """
    启动时立即执行一次预热
    """
    from .cache import warmup_cache
    from .market import MarketAnalysis
    from .sentiment import SentimentAnalysis
    
    print("🔥 开始初始缓存预热...")
    
    try:
        warmup_cache(MarketAnalysis.get_market_overview_v2)
    except Exception as e:
        print(f"  市场概览预热失败: {e}")
    
    try:
        warmup_cache(SentimentAnalysis.calculate_fear_greed_custom, symbol="sh000001", days=14)
    except Exception as e:
        print(f"  恐慌指数预热失败: {e}")
    
    try:
        warmup_cache(MarketAnalysis.get_sector_top)
        warmup_cache(MarketAnalysis.get_sector_bottom)
    except Exception as e:
        print(f"  板块排行预热失败: {e}")
        
    try:
        from .index import IndexAnalysis
        warmup_cache(IndexAnalysis.compare_indices)
    except Exception as e:
        print(f"  指数对比预热失败: {e}")

    try:
        from .fund import FundAnalysis
        warmup_cache(FundAnalysis.get_top_funds, indicator="近1年", top_n=10)
    except Exception as e:
        print(f"  基金排行预热失败: {e}")
    
    print("🔥 初始缓存预热完成")
