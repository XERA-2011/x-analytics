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
            import random
            import time as time_module
            # 错峰延迟 (0-10秒随机)，避免多个任务同时触发导致 API 限流
            stagger_delay = random.uniform(0, 10)
            time_module.sleep(stagger_delay)
            try:
                # 直接执行预热函数
                # 执行频率由 APScheduler 的 IntervalTrigger 控制
                # 不再在此处做分钟过滤（之前的逻辑有 BUG：任务触发时间与整点对不上）
                now = get_beijing_time()
                print(f"🔄 执行预热任务: {job_id} @ {now.strftime('%H:%M:%S')}")
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
    
    # 1. 恐慌贪婪指数 (30分/4小时)
    scheduler.add_market_job(
        job_id="warmup:cn:fear_greed",
        func=lambda: warmup_cache(CNFearGreedIndex.calculate, symbol="sh000001", days=14),
        market="market_cn"
    )



    # 3. 领涨/领跌板块 (已移除旧版接口)
    # scheduler.add_market_job(
    #     job_id="warmup:cn:gainers",
    #     func=lambda: warmup_cache(CNMarketLeaders.get_top_gainers),
    #     market="market_cn"
    # )
    # scheduler.add_market_job(
    #     job_id="warmup:cn:losers",
    #     func=lambda: warmup_cache(CNMarketLeaders.get_top_losers),
    #     market="market_cn"
    # )
    # scheduler.add_market_job(
    #     job_id="warmup:cn:sectors",
    #     func=lambda: warmup_cache(CNMarketLeaders.get_sector_leaders),
    #     market="market_cn"
    # )


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
    # 美国市场 (US Market)
    # =========================================================================

    # 1. CNN 恐慌指数
    scheduler.add_market_job(
        job_id="warmup:us:fear_cnn",
        func=lambda: warmup_cache(USFearGreedIndex.get_cnn_fear_greed),
        market="market_us"
    )
    
    # 2. 自定义恐慌指数
    scheduler.add_market_job(
        job_id="warmup:us:fear_custom",
        func=lambda: warmup_cache(USFearGreedIndex.calculate_custom_index),
        market="market_us"
    )

    # 3. 板块热度 & 领涨
    scheduler.add_market_job(
        job_id="warmup:us:heat",
        func=lambda: warmup_cache(USMarketHeat.get_sector_performance),
        market="market_us"
    )
    scheduler.add_market_job(
        job_id="warmup:us:leaders",
        func=lambda: warmup_cache(USMarketLeaders.get_leaders),
        market="market_us"
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
        func=lambda: warmup_cache(GoldSilverAnalysis.get_gold_silver_ratio),
        market="metals"
    )

    # 2. 现货价格
    scheduler.add_market_job(
        job_id="warmup:metals:prices",
        func=lambda: warmup_cache(MetalSpotPrice.get_spot_prices),
        market="metals"
    )

    # 3. 黄金恐慌贪婪
    scheduler.add_market_job(
        job_id="warmup:metals:fear",
        func=lambda: warmup_cache(GoldFearGreedIndex.calculate),
        market="metals"
    )

    # 4. 白银恐慌贪婪
    from ..modules.metals.fear_greed import SilverFearGreedIndex
    scheduler.add_market_job(
        job_id="warmup:metals:silver_fear",
        func=lambda: warmup_cache(SilverFearGreedIndex.calculate),
        market="metals"
    )

    # =========================================================================
    # 超买超卖信号 (Overbought/Oversold Signals)
    # =========================================================================
    from ..modules.signals.overbought_oversold import OverboughtOversoldSignal
    
    # A股超买超卖 (每30分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:cn",
        func=lambda: warmup_cache(OverboughtOversoldSignal.get_cn_signal, period="daily"),
        market="market_cn"
    )
    
    # 美股超买超卖 (每30分钟)
    scheduler.add_market_job(
        job_id="warmup:signals:us",
        func=lambda: warmup_cache(OverboughtOversoldSignal.get_us_signal, period="daily"),
        market="market_us"
    )
    
    # 黄金超买超卖 (每小时)
    scheduler.add_market_job(
        job_id="warmup:signals:gold",
        func=lambda: warmup_cache(OverboughtOversoldSignal.get_gold_signal, period="daily"),
        market="metals"
    )
    
    # 白银超买超卖 (每小时)
    scheduler.add_market_job(
        job_id="warmup:signals:silver",
        func=lambda: warmup_cache(OverboughtOversoldSignal.get_silver_signal, period="daily"),
        market="metals"
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
    # 基金数据 (Funds)
    # =========================================================================
    from ..modules.funds import FundRanking
    
    # 基金排行 (每天更新，4小时预热一次)
    scheduler.add_simple_job(
        job_id="warmup:funds:ranking",
        func=FundRanking._refresh_all_caches,
        interval_minutes=240
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

        # warmup_cache(CNMarketLeaders.get_top_gainers)
        # warmup_cache(CNMarketLeaders.get_top_losers)
        # warmup_cache(CNMarketLeaders.get_sector_leaders)
        
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
        warmup_cache(OverboughtOversoldSignal.get_us_signal, period="daily")
        time.sleep(5)
        warmup_cache(OverboughtOversoldSignal.get_gold_signal, period="daily")
        time.sleep(5)
        warmup_cache(OverboughtOversoldSignal.get_silver_signal, period="daily")
        
        logger.info("✅ 超买超卖信号预热完成")
        
        # 基金数据
        logger.info("⏳ 预热基金数据...")
        from ..modules.funds import FundRanking
        FundRanking._refresh_all_caches()
        logger.info("✅ 基金数据预热完成")
        
        # 后台继续预热次要数据

        warmup_cache(CNBonds.get_bond_market_analysis)
        warmup_cache(LPRAnalysis.get_lpr_rates)
        warmup_cache(USTreasury.get_us_bond_yields)

    except Exception as e:
        logger.error(f"❌ 初始预热过程中发生错误: {e}")
    
    logger.info("🔥 初始缓存预热结束")


def snapshot_daily_metrics():
    """每日市场快照（写入数据库）"""
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

