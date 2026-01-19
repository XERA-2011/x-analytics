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
    
    刷新策略：
    - 5分钟刷新 (交易时段)：恐慌指数、指数对比
    - 1小时刷新 (交易时段)：市场概览、领涨/领跌板块
    - 12小时刷新 (交易时段)：基金排行
    - 非交易时段：统一 24 小时刷新一次
    
    在 server.py 启动时调用
    """
    from .cache import warmup_cache
    from .market import MarketAnalysis
    from .sentiment import SentimentAnalysis
    
    # 非交易时段统一 24 小时 = 1440 分钟
    NON_TRADING_INTERVAL = 1440
    
    # =========================================================================
    # 5分钟刷新组：恐慌指数、指数对比
    # =========================================================================
    
    # 恐慌贪婪指数
    scheduler.add_warmup_job(
        job_id="warmup:sentiment:fear_greed",
        func=lambda: warmup_cache(SentimentAnalysis.calculate_fear_greed_custom, symbol="sh000001", days=14),
        trading_interval_minutes=5,
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )
    
    # 主要指数对比
    from .index import IndexAnalysis
    scheduler.add_warmup_job(
        job_id="warmup:index:compare",
        func=lambda: warmup_cache(IndexAnalysis.compare_indices),
        trading_interval_minutes=5,
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )
    
    # =========================================================================
    # 1小时刷新组：市场概览、领涨/领跌板块
    # =========================================================================
    
    # 市场概览
    scheduler.add_warmup_job(
        job_id="warmup:market:overview",
        func=lambda: warmup_cache(MarketAnalysis.get_market_overview_v2),
        trading_interval_minutes=60,
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )
    
    # 领涨板块
    scheduler.add_warmup_job(
        job_id="warmup:market:sector_top",
        func=lambda: warmup_cache(MarketAnalysis.get_sector_top),
        trading_interval_minutes=60,
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )
    
    # 领跌板块
    scheduler.add_warmup_job(
        job_id="warmup:market:sector_bottom",
        func=lambda: warmup_cache(MarketAnalysis.get_sector_bottom),
        trading_interval_minutes=60,
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )

    # =========================================================================
    # 12小时刷新组：基金排行
    # =========================================================================
    from .fund import FundAnalysis
    
    scheduler.add_warmup_job(
        job_id="warmup:fund:top",
        func=lambda: warmup_cache(FundAnalysis.get_top_funds, indicator="近1年", top_n=10),
        trading_interval_minutes=720,  # 12小时
        non_trading_interval_minutes=NON_TRADING_INTERVAL,
    )


def warmup_with_retry(func, name: str, max_retries: int = 3, *args, **kwargs) -> bool:
    """
    带指数退避重试的缓存预热
    
    Args:
        func: 要预热的被 @cached 装饰的函数
        name: 任务名称（用于日志）
        max_retries: 最大重试次数
        *args, **kwargs: 传递给函数的参数
    
    Returns:
        是否预热成功
    """
    import time
    from .cache import warmup_cache
    
    for attempt in range(max_retries):
        try:
            warmup_cache(func, *args, **kwargs)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                print(f"  ⚠️ {name}预热失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print(f"     {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ {name}预热失败 (已重试{max_retries}次): {e}")
                return False
    return False


def initial_warmup():
    """
    启动时立即执行一次预热（带重试机制）
    """
    from .market import MarketAnalysis
    from .sentiment import SentimentAnalysis
    
    print("🔥 开始初始缓存预热...")
    
    success_count = 0
    total_count = 5
    
    # 市场概览
    if warmup_with_retry(MarketAnalysis.get_market_overview_v2, "市场概览"):
        success_count += 1
    
    # 恐慌贪婪指数
    if warmup_with_retry(
        SentimentAnalysis.calculate_fear_greed_custom, 
        "恐慌指数",
        3,
        symbol="sh000001", 
        days=14
    ):
        success_count += 1
    
    # 板块排行
    if warmup_with_retry(MarketAnalysis.get_sector_top, "领涨板块"):
        success_count += 1
    warmup_with_retry(MarketAnalysis.get_sector_bottom, "领跌板块")
    
    # 指数对比
    try:
        from .index import IndexAnalysis
        if warmup_with_retry(IndexAnalysis.compare_indices, "指数对比"):
            success_count += 1
    except ImportError:
        print("  ⚠️ 指数分析模块未找到，跳过")

    # 基金排行
    try:
        from .fund import FundAnalysis
        if warmup_with_retry(
            FundAnalysis.get_top_funds, 
            "基金排行",
            3,
            indicator="近1年", 
            top_n=10
        ):
            success_count += 1
    except ImportError:
        print("  ⚠️ 基金分析模块未找到，跳过")
    
    print(f"🔥 初始缓存预热完成 ({success_count}/{total_count} 成功)")
