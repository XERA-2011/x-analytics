"""
基金涨跌幅排行模块

数据源: 东方财富-天天基金 (via AkShare)

策略: 只缓存「全部」类型数据，其他类型从缓存中本地过滤
      避免多个并发请求触发东方财富限流
"""

from typing import Dict, Any, List
import akshare as ak
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import akshare_call_with_retry, safe_float, get_beijing_time
from ...core.logger import logger


class FundRanking:
    """基金涨跌幅排行"""

    # 支持的基金类型及其关键词映射
    FUND_TYPE_KEYWORDS = {
        "全部": None,         # 不过滤
        "股票型": "股票",
        "混合型": "混合",
        "债券型": "债券",
        "指数型": "指数",
        "FOF": "FOF",
        "QDII": "QDII"
    }

    @staticmethod
    def _refresh_all_caches() -> bool:
        """
        全量刷新所有类型的基金缓存
        1. 获取全量数据 (19k+)
        2. 按类型拆分
        3. 截取前 100 条 (减少 Redis 传输体积)
        4. 并行写入缓存
        """
        try:
            logger.info("🔄 开始全量刷新基金数据...")
            
            # 1. 只有这一步调用 AkShare
            df = akshare_call_with_retry(
                ak.fund_open_fund_rank_em,
                symbol="全部"
            )

            if df is None or df.empty:
                raise ValueError("暂无基金数据")

            # 2. 解析为 list of dict
            all_funds = FundRanking._parse_fund_data(df)
            
            # 3. 按类型处理并写入缓存
            from ...core.cache import cache
            
            for type_name, keyword in FundRanking.FUND_TYPE_KEYWORDS.items():
                # 过滤
                if keyword:
                    filtered_funds = [f for f in all_funds if keyword in f.get("name", "")]
                else:
                    filtered_funds = all_funds # 全部
                
                # 排序
                # 涨幅榜: 跌幅从大到小
                gainers = sorted(filtered_funds, key=lambda x: x.get("daily_change") or -999, reverse=True)
                # 跌幅榜: 跌幅从小到大
                losers = sorted(filtered_funds, key=lambda x: x.get("daily_change") or 999, reverse=False)

                # 截取 Top 50 (UI请求10条，缓存保留余量)
                top_gainers = gainers[:50]
                top_losers = losers[:50]
                
                cache_key = f"funds:ranking:{type_name}"
                
                # 构造新缓存结构: 分离涨跌榜
                val = {
                    "status": "ok",
                    "fund_type": type_name,
                    "total": len(filtered_funds),
                    "data": {
                        "gainers": top_gainers,
                        "losers": top_losers
                    },
                    "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 写入 Redis (TTL 24h)
                cache.set(cache_key, val, ttl=settings.CACHE_TTL.get("funds", 86400))
                
            logger.info("✅ 基金全量刷新完成，已更新所有分榜缓存")
            return True
            
        except Exception as e:
            logger.error(f"❌ 基金全量刷新失败: {e}")
            return False

    @staticmethod
    def _parse_fund_data(df) -> List[Dict[str, Any]]:
        """解析 DataFrame 为列表"""
        funds = []
        for _, row in df.iterrows():
            fund = {
                "code": str(row.get("基金代码", "")),
                "name": str(row.get("基金简称", "")),
                "date": str(row.get("日期", "")),
                "nav": safe_float(row.get("单位净值"), None),
                "acc_nav": safe_float(row.get("累计净值"), None),
                "daily_change": safe_float(row.get("日增长率"), None),
                "week_change": safe_float(row.get("近1周"), None),
                "month_change": safe_float(row.get("近1月"), None),
                "quarter_change": safe_float(row.get("近3月"), None),
                "half_year_change": safe_float(row.get("近6月"), None),
                "year_change": safe_float(row.get("近1年"), None),
                "ytd_change": safe_float(row.get("今年来"), None),
                "fee": str(row.get("手续费", ""))
            }
            funds.append(fund)
        return funds

    @staticmethod
    def get_ranking(fund_type: str = "全部", limit: int = 10) -> Dict[str, Any]:
        """
        获取基金涨跌幅排行 (Top N 涨幅 & Top N 跌幅)
        """
        # 验证基金类型
        if fund_type not in FundRanking.FUND_TYPE_KEYWORDS:
            fund_type = "全部"

        cache_key = f"funds:ranking:{fund_type}"
        from ...core.cache import cache
        
        # 1. 尝试读取缓存
        data = cache.get(cache_key)
        
        # 2. 缓存命中
        if data:
            if isinstance(data, dict):
                inner_data = data.get("data", {})
                # 检查是否是新结构 (包含 gainers/losers)
                if isinstance(inner_data, dict) and "gainers" in inner_data:
                    return {
                        "status": "ok",
                        "data": {
                            "gainers": inner_data["gainers"][:limit],
                            "losers": inner_data["losers"][:limit],
                            "total": data.get("total", 0),
                            "fund_type": data.get("fund_type", "全部"),
                            "update_time": data.get("update_time")
                        }
                    }
                
                # 兼容旧缓存结构 (list) - 临时回退逻辑
                # 兼容旧缓存结构: 如果发现是旧数据，视为缓存未命中，触发刷新
                logger.warning(f"⚠️ 发现旧版缓存结构 ({fund_type})，触发后台刷新...")
        
        # 3. 缓存未命中 或 旧数据 -> 触发后台刷新
        # 检查是否已有刷新任务在运行
        refresh_key = "funds:global_refresh_lock"
        if cache.get(refresh_key):
             return {
                 "status": "warming_up", 
                 "data": {
                     "gainers": [], "losers": [],
                     "message": "数据结构升级中，正在后台刷新..."
                 }
             }
             
        # 启动后台刷新任务 (使用线程)
        import threading
        def run_refresh():
            # 简单的防并发锁
            cache.set(refresh_key, "1", ttl=300) 
            try:
                FundRanking._refresh_all_caches()
            finally:
                cache.delete(refresh_key)
                
        threading.Thread(target=run_refresh, daemon=True).start()
        
        return {
            "status": "warming_up", 
            "data": {
                "gainers": [], "losers": [],
                "message": "数据结构升级中，请稍后刷新"
            }
        }
