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
        self._jobs: set = set()
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

        use_warmup_cache: bool = False,
        trading_interval_minutes: Optional[int] = None,
        non_trading_max_age_seconds: Optional[int] = None,
        **kwargs,
    ):
        """
        添加市场相关的预热任务

        Args:
            job_id: 任务 ID
            func: 预热函数
            market: 市场类型 ('cn_market', 'us_market', 'metals')

            trading_interval_minutes: 交易时段执行间隔，默认读取配置
            non_trading_max_age_seconds: 非交易时段缓存最大保鲜时间，避免短 TTL 指标休市持续打上游
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
                            meta = cached_data["_meta"]
                            fresh_until = meta.get("expire_at", 0)
                            if non_trading_max_age_seconds is not None:
                                cached_at = meta.get("cached_at", 0)
                                fresh_until = cached_at + non_trading_max_age_seconds

                            # 缓存仍在非交易保鲜窗口内，无需刷新
                            if _time.time() < fresh_until:
                                return
                except Exception:
                    pass  # 检查失败时 fallthrough 执行预热

            # 错峰延迟 (0-10秒随机)，避免多个任务同时触发导致 API 限流
            stagger_delay = random.uniform(0, 10)
            time_module.sleep(stagger_delay)
            start = time_module.time()
            try:
                now = get_beijing_time()
                logger.info(f"执行预热任务: {job_id} @ {now.strftime('%H:%M:%S')}")
                if use_warmup_cache:
                    from .cache import warmup_cache
                    warmup_cache(func, **kwargs)
                else:
                    func(**kwargs)
                self._record_execution(job_id, True, time_module.time() - start)
            except Exception as e:
                self._record_execution(job_id, False, time_module.time() - start, e)
                logger.error(f"预热任务失败 [{job_id}]: {e}")

        # 使用最小间隔注册任务，在函数内部进行智能过滤
        if trading_interval_minutes is not None:
            interval_minutes = max(1, trading_interval_minutes)
        else:
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
        self._jobs.add(job_id)
        logger.info(f"注册智能预热任务: {job_id} (市场: {market})")

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
                logger.error(f"任务失败 [{job_id}]: {e}")

        self.scheduler.add_job(
            job_wrapper,
            IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            replace_existing=True,
        )
        self._jobs.add(job_id)
        logger.info(f"注册任务: {job_id} (间隔: {interval_minutes}分钟)")

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
                logger.error(f"定时任务失败 [{job_id}]: {e}")

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
            self._jobs.add(job_id)
            logger.info(f"注册定时任务: {job_id} ({cron_expr})")

    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("智能调度器已启动")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("智能调度器已关闭")

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




# 全局调度器实例
scheduler = SmartScheduler.get_instance()


@lru_cache(maxsize=2)
def _get_trading_days_cache(year: int) -> set:
    """获取指定年份的交易日历（缓存）"""
    try:
        logger.info(f"正在获取 {year} 年交易日历...")
        tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
        df = tool_trade_date_hist_sina_df
        import pandas as pd
        trade_dates = set(pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d").tolist())
        return trade_dates
    except Exception as e:
        logger.warning(f"获取交易日历失败: {e}")
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
    logger.info("设置默认预热任务...")
    
    from .cache import warmup_cache
    from ..modules.market_asia import (
        CNFearGreedIndex,
        CNMarketLeaders,
        CNIndices,
        CNBonds,
        LPRAnalysis,
    )
    from ..modules.market_western import (
        USFearGreedIndex,
        USMarketHeat,
        USTreasury,
        USMarketLeaders
    )
    from ..modules.metals import GoldSilverAnalysis, MetalSpotPrice, GoldFearGreedIndex


    # =========================================================================
    # 亚洲市场 (Asia Market)
    # =========================================================================
    
    # 1. 恐慌贪婪指数 (10分/4小时)
    scheduler.add_market_job(
        job_id="warmup:asia:fear_greed",
        func=CNFearGreedIndex.calculate,
        market="market_asia",
        use_warmup_cache=True,
        trading_interval_minutes=5,
        non_trading_max_age_seconds=settings.CACHE_TTL["fear_greed_stale"],
        symbol="sh000001",
        days=14,
    )




    # scheduler.add_market_job(
    #     job_id="warmup:asia:sectors",
    #     func=CNMarketLeaders.get_all_sectors,
    #     market="market_asia",
    #     use_warmup_cache=True,
    # )

    scheduler.add_market_job(
        job_id="warmup:asia:indices",
        func=CNIndices.get_indices,
        market="market_asia",
        use_warmup_cache=True,
    )

    scheduler.add_simple_job(
        job_id="warmup:asia:bonds",
        func=lambda: warmup_cache(CNBonds.get_bond_market_analysis),
        interval_minutes=240
    )
    scheduler.add_simple_job(
        job_id="warmup:asia:lpr",
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
        trading_interval_minutes=5,
        non_trading_max_age_seconds=settings.CACHE_TTL["fear_greed_stale"],
    )

    # =========================================================================
    # 欧美市场 (Western Market)
    # =========================================================================

    # 1. CNN 恐慌指数代理：开盘期 5 分钟刷新，休市保留最近有效值
    scheduler.add_market_job(
        job_id="warmup:western:fear_cnn",
        func=USFearGreedIndex.get_cnn_fear_greed,
        market="market_western",
        use_warmup_cache=True,
        trading_interval_minutes=5,
        non_trading_max_age_seconds=settings.CACHE_TTL["fear_greed_stale"],
    )
    
    # 2. 自定义恐慌指数
    scheduler.add_market_job(
        job_id="warmup:western:fear_custom",
        func=USFearGreedIndex.calculate_custom_index,
        market="market_western",
        use_warmup_cache=True,
        trading_interval_minutes=5,
        non_trading_max_age_seconds=settings.CACHE_TTL["fear_greed_stale"],
    )

    # 3. 板块热度 & 领涨 (每10分钟)
    scheduler.add_simple_job(
        job_id="warmup:western:heat",
        func=lambda: warmup_cache(USMarketHeat.get_sector_performance),
        interval_minutes=10
    )
    scheduler.add_simple_job(
        job_id="warmup:western:leaders",
        func=lambda: warmup_cache(USMarketLeaders.get_leaders),
        interval_minutes=10
    )

    # 4. 美债 (低频)
    scheduler.add_simple_job(
        job_id="warmup:western:treasury",
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
        trading_interval_minutes=5,
    )

    # 4. 白银恐慌贪婪
    from ..modules.metals.fear_greed import SilverFearGreedIndex
    scheduler.add_market_job(
        job_id="warmup:metals:silver_fear",
        func=SilverFearGreedIndex.calculate,
        market="metals",
        use_warmup_cache=True,
        trading_interval_minutes=5,
    )
    # =========================================================================
    # ETF 市场 (ETF Market)
    # =========================================================================
    from ..modules.etf import ETFHeatmap

    scheduler.add_market_job(
        job_id="warmup:etf:heatmap",
        func=ETFHeatmap.get_heatmap_data,
        market="market_cn",
        use_warmup_cache=True,
        trading_interval_minutes=10,
        non_trading_max_age_seconds=settings.CACHE_TTL["etf_heatmap"],
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
    
    # 美股超买超卖 (每10分钟)
    scheduler.add_simple_job(
        job_id="warmup:signals:us",
        func=lambda: warmup_cache(
            OverboughtOversoldSignal.get_us_signal, period="daily"
        ),
        interval_minutes=10
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
            logger.info("执行开盘前预热...")
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
    from ..modules.market_asia import (
        CNFearGreedIndex,
        CNMarketLeaders,
        CNIndices,
        CNBonds,
        LPRAnalysis,
    )
    from ..modules.market_western import (
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
        # warmup_cache(CNMarketLeaders.get_all_sectors)
        warmup_cache(CNIndices.get_indices)


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

        # ETF
        from ..modules.etf import ETFHeatmap
        warmup_cache(ETFHeatmap.get_heatmap_data)

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


# 主事件循环引用，由 server.py lifespan 启动时通过 set_main_loop() 注入
_main_loop = None


def set_main_loop(loop) -> None:
    """保存 FastAPI 主事件循环引用，供后台线程的 DB 操作使用。"""
    global _main_loop
    _main_loop = loop


def _submit_to_main_loop(coro) -> None:
    """将协程提交到 FastAPI 主事件循环执行。

    仅允许从后台线程调用（如 APScheduler）。
    如果从主循环线程调用，改用 create_task 避免自锁阻塞。
    """
    import asyncio

    if _main_loop is None or _main_loop.is_closed():
        logger.warning("主事件循环不可用，跳过本次 DB 操作")
        coro.close()
        return

    try:
        # 判断当前是否已在目标事件循环内——如果是，不能 .result() 等待，会自锁
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is _main_loop:
            _main_loop.create_task(coro)
            return

        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        future.result(timeout=30)
    except Exception as e:
        coro.close()
        logger.error(f"提交协程到主循环失败: {e}")


def snapshot_daily_metrics() -> None:
    """每日市场快照（写入数据库）

    同步行情计算在 APScheduler 后台线程执行，
    只将轻量的 DB 写入提交到 FastAPI 主事件循环。
    """
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return

    try:
        logger.info("📸 开始执行数据库快照...")
        from analytics.modules.market_cn import CNFearGreedIndex
        from analytics.modules.market_us import USFearGreedIndex
        from analytics.modules.market_hk.fear_greed import HKFearGreed
        from analytics.modules.metals import GoldFearGreedIndex
        from analytics.modules.metals.fear_greed import SilverFearGreedIndex
        from analytics.modules.signals.overbought_oversold import OverboughtOversoldSignal
        from datetime import date

        today = date.today()
        snapshots = []

        # 1. ASIA
        cn_res = CNFearGreedIndex.calculate(symbol="sh000001", days=14)
        if cn_res and "score" in cn_res:
            snapshots.append({"market": "ASIA", "indicator": "fear_greed", "score": cn_res["score"], "level": cn_res["level"]})

        # 2. WESTERN
        us_res = USFearGreedIndex.calculate_custom_index()
        if us_res and "score" in us_res:
            snapshots.append({"market": "WESTERN", "indicator": "fear_greed", "score": us_res["score"], "level": us_res["level"]})

        # 3. HK
        hk_res = HKFearGreed.get_data()
        if hk_res and "score" in hk_res:
            snapshots.append({"market": "HK", "indicator": "fear_greed", "score": hk_res["score"], "level": hk_res["level"]})

        # 4. Gold
        gold_res = GoldFearGreedIndex.calculate()
        if gold_res and "score" in gold_res:
            snapshots.append({"market": "Gold", "indicator": "fear_greed", "score": gold_res["score"], "level": gold_res["level"]})

        # 5. Silver
        silver_res = SilverFearGreedIndex.calculate()
        if silver_res and "score" in silver_res:
            snapshots.append({"market": "Silver", "indicator": "fear_greed", "score": silver_res["score"], "level": silver_res["level"]})
            
        # OBO Signals
        cn_obo = OverboughtOversoldSignal.get_cn_signal("daily")
        if cn_obo and "score" in cn_obo:
            snapshots.append({"market": "ASIA", "indicator": "overbought_oversold", "score": cn_obo["score"], "level": cn_obo.get("signal", "neutral")})
            
        us_obo = OverboughtOversoldSignal.get_us_signal("daily")
        if us_obo and "score" in us_obo:
            snapshots.append({"market": "WESTERN", "indicator": "overbought_oversold", "score": us_obo["score"], "level": us_obo.get("signal", "neutral")})
            
        hk_obo = OverboughtOversoldSignal.get_hk_signal("daily")
        if hk_obo and "score" in hk_obo:
            snapshots.append({"market": "HK", "indicator": "overbought_oversold", "score": hk_obo["score"], "level": hk_obo.get("signal", "neutral")})

        async def _db_write():
            from analytics.models.sentiment import SentimentHistory
            for snap in snapshots:
                await SentimentHistory.update_or_create(
                    date=today,
                    market=snap["market"],
                    indicator_type=snap["indicator"],
                    defaults={"score": snap["score"], "level": snap["level"]}
                )
            logger.info(f"✅ [DB] 已保存今日快照: {len(snapshots)} 条记录")

        _submit_to_main_loop(_db_write())

    except Exception as e:
        logger.error(f"❌ 数据库快照失败: {e}")


def cleanup_old_data() -> None:
    """清理30天前的旧数据"""
    from .db import DB_AVAILABLE
    if not DB_AVAILABLE:
        return

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

    _submit_to_main_loop(_async_cleanup())
