#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
智能调度器模块
基于交易时间的智能缓存预热调度
"""

import time as time_module
from collections import deque
from datetime import date
from typing import Callable, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from functools import lru_cache
import akshare as ak
from .config import settings
from .utils import get_beijing_time
from .logger import logger


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
        self._execution_log: deque = deque(maxlen=50)  # 最近50条执行记录

    def _record_execution(self, job_id, success, duration, error=None):
        """记录任务执行结果"""
        self._execution_log.append({
            "job_id": job_id,
            "timestamp": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            "success": success,
            "duration_s": round(duration, 2),
            "error": str(error) if error else None,
        })

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
        use_warmup_cache: bool = False,
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
            """智能预热函数 — 交易时段高频刷新，非交易时段按需保鲜"""
            import random
            from .utils import is_trading_time

            trading = is_trading_time(market)

            if not trading:
                # 非交易时段：检查缓存是否仍然新鲜，如果是则跳过
                # 只有当缓存的逻辑 TTL 已过期时才执行预热，确保数据不断档
                try:
                    _func = func if not kwargs else lambda: func(**kwargs)
                    _target = func
                    prefix = getattr(_target, '_cache_prefix', None)
                    if prefix:
                        from .cache import make_cache_key, cache as _cache
                        import time as _time
                        cache_key = make_cache_key(prefix, **kwargs)
                        cached_data = _cache.get(cache_key)
                        if cached_data and isinstance(cached_data, dict) and "_meta" in cached_data:
                            expire_at = cached_data["_meta"].get("expire_at", 0)
                            # 缓存逻辑 TTL 还没过期，无需刷新
                            if _time.time() < expire_at:
                                return
                except Exception:
                    pass  # 检查失败时 fallthrough 执行预热

            # 错峰延迟 (0-10秒随机)，避免多个任务同时触发导致 API 限流
            stagger_delay = random.uniform(0, 10)
            time_module.sleep(stagger_delay)
            start = time_module.time()
            try:
                now = get_beijing_time()
                print(f"🔄 执行预热任务: {job_id} @ {now.strftime('%H:%M:%S')}")
                if use_warmup_cache:
                    from .cache import warmup_cache
                    warmup_cache(func, **kwargs)
                else:
                    func(**kwargs)
                self._record_execution(job_id, True, time_module.time() - start)
            except Exception as e:
                self._record_execution(job_id, False, time_module.time() - start, e)
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
            start = time_module.time()
            try:
                func(**kwargs)
                self._record_execution(job_id, True, time_module.time() - start)
            except Exception as e:
                self._record_execution(job_id, False, time_module.time() - start, e)
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
            start = time_module.time()
            try:
                func(**kwargs)
                self._record_execution(job_id, True, time_module.time() - start)
            except Exception as e:
                self._record_execution(job_id, False, time_module.time() - start, e)
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
            "recent_executions": list(self._execution_log),
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
    
    from .cache import warmup_cache
    from ..modules.market_cn import (
        CNFearGreedIndex,
        CNMarketLeaders,
        CNBonds,
        LPRAnalysis,
    )
    from ..modules.market_us import (
        USFearGreedIndex,
        USMarketHeat,
        USTreasury,
        USMarketLeaders
    )
    from ..modules.metals import GoldSilverAnalysis, MetalSpotPrice, GoldFearGreedIndex


    # =========================================================================
    # 中国市场 (CN Market)
    # =========================================================================
    
    # 1. 恐慌贪婪指数 (10分/4小时)
    scheduler.add_market_job(
        job_id="warmup:cn:fear_greed",
        func=CNFearGreedIndex.calculate,
        market="market_cn",
        use_warmup_cache=True,
        symbol="sh000001",
        days=14,
    )




    scheduler.add_market_job(
        job_id="warmup:cn:sectors",
        func=CNMarketLeaders.get_all_sectors,
        market="market_cn",
        use_warmup_cache=True,
    )

    scheduler.add_simple_job(
        job_id="warmup:cn:bonds",
        func=lambda: warmup_cache(CNBonds.get_bond_market_analysis),
        interval_minutes=240
    )
    scheduler.add_simple_job(
        job_id="warmup:cn:lpr",
        func=lambda: warmup_cache(LPRAnalysis.get_lpr_rates),
        interval_minutes=240
    )

    # =========================================================================
    # 香港市场 (HK Market)
    # =========================================================================

    from ..modules.market_hk import HKIndices
    from ..modules.market_hk.fear_greed import HKFearGreed

    # 1. 港股指数 & 板块
    scheduler.add_market_job(
        job_id="warmup:hk:indices",
        func=HKIndices.get_market_data,
        market="market_hk",
        use_warmup_cache=True,
    )

    # 2. 港股恐慌贪婪
    scheduler.add_market_job(
        job_id="warmup:hk:fear_greed",
        func=HKFearGreed.get_data,
        market="market_hk",
        use_warmup_cache=True,
    )

    # =========================================================================
    # 美国市场 (US Market)
    # =========================================================================

    # 1. CNN 恐慌指数 (10分钟无条件刷新，美股日线数据收盘后固定)
    scheduler.add_simple_job(
        job_id="warmup:us:fear_cnn",
        func=lambda: warmup_cache(USFearGreedIndex.get_cnn_fear_greed),
        interval_minutes=10
    )
    
    # 2. 自定义恐慌指数
    scheduler.add_simple_job(
        job_id="warmup:us:fear_custom",
        func=lambda: warmup_cache(USFearGreedIndex.calculate_custom_index),
        interval_minutes=10
    )

    # 3. 板块热度 & 领涨
    scheduler.add_simple_job(
        job_id="warmup:us:heat",
        func=lambda: warmup_cache(USMarketHeat.get_sector_performance),
        interval_minutes=60
    )
    scheduler.add_simple_job(
        job_id="warmup:us:leaders",
        func=lambda: warmup_cache(USMarketLeaders.get_leaders),
        interval_minutes=60
    )

    # 4. 美债 (低频)
    scheduler.add_simple_job(
        job_id="warmup:us:treasury",
        func=lambda: warmup_cache(USTreasury.get_us_bond_yields),
        interval_minutes=240
    )

    # =========================================================================
    # 贵金属 (Metals)
    # =========================================================================

    # 1. 金银比
    scheduler.add_market_job(
        job_id="warmup:metals:ratio",
        func=GoldSilverAnalysis.get_gold_silver_ratio,
        market="metals",
        use_warmup_cache=True,
    )

    # 2. 现货价格
    scheduler.add_market_job(
        job_id="warmup:metals:prices",
        func=MetalSpotPrice.get_spot_prices,
        market="metals",
        use_warmup_cache=True,
    )

    # 3. 黄金恐慌贪婪
    scheduler.add_market_job(
        job_id="warmup:metals:fear",
        func=GoldFearGreedIndex.calculate,
        market="metals",
        use_warmup_cache=True,
    )

    # 4. 白银恐慌贪婪
    from ..modules.metals.fear_greed import SilverFearGreedIndex
    scheduler.add_market_job(
        job_id="warmup:metals:silver_fear",
        func=SilverFearGreedIndex.calculate,
        market="metals",
        use_warmup_cache=True,
    )

    # =========================================================================
    # 超买超卖信号 (Overbought/Oversold Signals)
    # =========================================================================
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    
    # A股超买超卖 (每10分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:cn",
        func=OverboughtOversoldSignal.get_cn_signal,
        market="market_cn",
        use_warmup_cache=True,
        period="daily",
    )
    
    # 美股超买超卖 (每60分钟，与其他美股任务保持一致)
    scheduler.add_simple_job(
        job_id="warmup:signals:us",
        func=lambda: warmup_cache(
            OverboughtOversoldSignal.get_us_signal, period="daily"
        ),
        interval_minutes=60
    )
    
    # 港股超买超卖 (每10分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:hk",
        func=OverboughtOversoldSignal.get_hk_signal,
        market="market_hk",
        use_warmup_cache=True,
        period="daily",
    )
    
    # 黄金超买超卖 (每10分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:gold",
        func=OverboughtOversoldSignal.get_gold_signal,
        market="metals",
        use_warmup_cache=True,
        period="daily",
    )
    
    # 白银超买超卖 (每10分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:silver",
        func=OverboughtOversoldSignal.get_silver_signal,
        market="metals",
        use_warmup_cache=True,
        period="daily",
    )

    # =========================================================================
    # 固定时间任务
    # =========================================================================
    
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

    # =========================================================================
    # 数据库持久化任务
    # =========================================================================
    
    # 1. 每日记录 (收盘后 15:30)
    scheduler.add_cron_job(
        job_id="db:snapshot_daily",
        func=snapshot_daily_metrics,
        cron_expr="30 15 * * 1-5", 
    )

    # 2. 数据清理 (每天凌晨 00:00) - 保留 30 天
    scheduler.add_cron_job(
        job_id="db:cleanup",
        func=cleanup_old_data,
        cron_expr="0 0 * * *", 
    )


def initial_warmup():
    """启动时立即执行一次预热"""
    logger.info("🔥 开始初始缓存预热...")
    
    from .cache import warmup_cache
    from ..modules.market_cn import (
        CNFearGreedIndex,
        CNMarketLeaders,
        CNBonds,
        LPRAnalysis,
    )
    from ..modules.market_us import (
        USFearGreedIndex,
        USMarketHeat,
        USTreasury,
        USMarketLeaders
    )
    from ..modules.metals import GoldSilverAnalysis, MetalSpotPrice, GoldFearGreedIndex

    
    try:
        # 使用线程池或简单顺序执行 (这里为了简单使用顺序，因 warmup_cache 内部有锁且 Server 是异步启动)
        # 也可以考虑并行，但 akshare 某些接口有并发限制
        
        # CN
        warmup_cache(CNFearGreedIndex.calculate, symbol="sh000001", days=14)
        warmup_cache(CNMarketLeaders.get_all_sectors)


        # US
        warmup_cache(USFearGreedIndex.get_cnn_fear_greed)
        warmup_cache(USFearGreedIndex.calculate_custom_index)
        warmup_cache(USMarketHeat.get_sector_performance)
        warmup_cache(USMarketLeaders.get_leaders)

        # Metals
        warmup_cache(GoldSilverAnalysis.get_gold_silver_ratio)
        warmup_cache(MetalSpotPrice.get_spot_prices)
        warmup_cache(GoldFearGreedIndex.calculate)
        from ..modules.metals.fear_greed import SilverFearGreedIndex
        warmup_cache(SilverFearGreedIndex.calculate)

        # HK
        from ..modules.market_hk import HKIndices
        from ..modules.market_hk.fear_greed import HKFearGreed
        warmup_cache(HKIndices.get_market_data)
        warmup_cache(HKFearGreed.get_data)

        logger.info("✅ 核心指标预热完成")
        
        # 超买超卖信号 (延迟执行，避免与核心数据预热同时请求导致 IP 被封)
        import time
        logger.info("⏳ 等待 60s 后预热超买超卖信号...")
        time.sleep(60)
        
        from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
        warmup_cache(OverboughtOversoldSignal.get_cn_signal, period="daily")
        time.sleep(5)  # 每个信号间隔 5s
        warmup_cache(OverboughtOversoldSignal.get_hk_signal, period="daily")
        time.sleep(5)
        warmup_cache(OverboughtOversoldSignal.get_us_signal, period="daily")
        time.sleep(5)
        warmup_cache(OverboughtOversoldSignal.get_gold_signal, period="daily")
        time.sleep(5)
        warmup_cache(OverboughtOversoldSignal.get_silver_signal, period="daily")
        
        logger.info("✅ 超买超卖信号预热完成")
        
        # 后台继续预热次要数据

        warmup_cache(CNBonds.get_bond_market_analysis)
        warmup_cache(LPRAnalysis.get_lpr_rates)
        warmup_cache(USTreasury.get_us_bond_yields)

    except Exception as e:
        logger.error(f"❌ 初始预热过程中发生错误: {e}")
    
    logger.info("🔥 初始缓存预热结束")


def snapshot_daily_metrics():
    """每日市场快照（写入数据库）"""
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return

    import asyncio
    
    async def _async_snapshot():
        try:
            logger.info("📸 开始执行数据库快照...")
            from analytics.modules.market_cn import CNFearGreedIndex
            from analytics.models.sentiment import SentimentHistory
            from datetime import date
            
            # 1. 记录 CN 恐慌指数
            # 注意：这里我们重新计算一次，以确保是最新的
            result = CNFearGreedIndex.calculate(symbol="sh000001", days=14)
            if result and "score" in result:
                await SentimentHistory.update_or_create(
                    date=date.today(),
                    market="CN",
                    defaults={
                        "score": result["score"],
                        "level": result["level"]
                    }
                )
                logger.info(f"✅ [DB] 已保存今日恐慌指数: {result['score']}")
            
        except Exception as e:
            logger.error(f"❌ 数据库快照失败: {e}")

    # 在同步环境运行异步任务
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(_async_snapshot())


def cleanup_old_data():
    """清理30天前的旧数据"""
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return

    import asyncio
    from datetime import date, timedelta
    
    async def _async_cleanup():
        try:
            from analytics.models.sentiment import SentimentHistory
            
            cutoff_date = date.today() - timedelta(days=30)
            deleted_count = await SentimentHistory.filter(date__lt=cutoff_date).delete()
            
            if deleted_count > 0:
                logger.info(f"🧹 [DB] 已清理旧数据: {deleted_count} 条 (before {cutoff_date})")
            else:
                logger.info("🧹 [DB] 无需清理旧数据")
                
        except Exception as e:
            logger.error(f"❌ 数据清理失败: {e}")

    # 在同步环境运行异步任务
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(_async_cleanup())
