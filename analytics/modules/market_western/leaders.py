"""
欧美市场主要指数与领涨分析
"""

import akshare as ak
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.data_provider import data_provider
from ...core.logger import logger


class USMarketLeaders:
    """欧美市场主要指数与分析"""

    @staticmethod
    @cached("market_us:indices", ttl=settings.CACHE_TTL["market_heat"], stale_ttl=settings.CACHE_TTL["market_heat"] * settings.STALE_TTL_RATIO)
    def get_leaders() -> Dict[str, Any]:
        """
        获取欧美市场主要指数 (纳斯达克, 标普500, 道琼斯, 欧洲斯托克50, 英国富时100, 德国DAX30, 法国CAC40)
        """
        indices_data = []
        
        # 定义欧美指数代码
        indices_map = [
            {"name": "纳斯达克", "code": "NDX"},
            {"name": "标普500", "code": "SPX"},
            {"name": "道琼斯", "code": "DJIA"},
            {"name": "欧洲斯托克50", "code": "SX5E"},
            {"name": "英国富时100", "code": "FTSE"},
            {"name": "德国DAX30", "code": "GDAXI"},
            {"name": "法国CAC40", "code": "FCHI"},
        ]

        try:
            logger.info("📊 获取欧美市场主要指数...")
            df = data_provider.get_global_indices_spot()
            
            if df.empty:
                raise ValueError("获取全球指数数据为空")

            df_map = df.set_index("代码").to_dict(orient="index")
            
            for item in indices_map:
                code = item["code"]
                if code in df_map:
                    row = df_map[code]
                    current_price = safe_float(row["最新价"])
                    change_amount = safe_float(row["涨跌额"])
                    change_pct = safe_float(row["涨跌幅"])
                    
                    indices_data.append({
                        "name": item["name"],
                        "code": code,
                        "price": current_price,
                        "change_amount": change_amount,
                        "change_pct": change_pct
                    })
                else:
                    logger.warning(f"⚠️ 欧美指数 {item['name']} 未能在行情中找到，跳过")

            core_index_count = sum(1 for item in indices_data if item.get("code") in {"NDX", "SPX", "DJIA"})
            if core_index_count != 3:
                logger.error("❌ 欧美核心指数数据不完整: expected=3 US indices, actual=%s", core_index_count)
                return {"error": "欧美核心指数数据不完整"}

            # 添加中概股 (使用 PGJ ETF 作为代理 - Invesco Golden Dragon China ETF)
            try:
                # 使用 stock_us_daily (Sina源) 获取 PGJ 数据，避开 EM 接口屏蔽
                df_cne = akshare_call_with_retry(ak.stock_us_daily, symbol='PGJ', adjust="qfq")
                if not df_cne.empty and len(df_cne) >= 2:
                    latest = df_cne.iloc[-1]
                    prev = df_cne.iloc[-2]
                    
                    current_price = safe_float(latest["close"])
                    prev_close = safe_float(prev["close"])
                    
                    # 注入极速实时价格
                    from ...core.us_spot_helper import get_us_spot_direct
                    spot_data = get_us_spot_direct(["PGJ"])
                    if spot_data and "PGJ" in spot_data:
                        spot = spot_data["PGJ"]
                        current_price = spot["price"]
                        if spot["change_pct"] is not None:
                            prev_close = current_price / (1 + spot["change_pct"] / 100)
                    
                    if current_price and prev_close:
                        change_amount = current_price - prev_close
                        change_pct = change_amount / prev_close * 100
                        indices_data.append({
                            "name": "中概股",
                            "code": "PGJ",
                            "price": current_price,
                            "change_amount": change_amount,
                            "change_pct": change_pct
                        })
            except Exception as e:
                 logger.warning(f"⚠️ 获取中概股数据失败: {e}")
            if not indices_data:
                logger.error("❌ 所有欧美指数数据获取失败")
                return {"error": "无法获取欧美指数实时数据"}

            return {
                "indices": indices_data,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            logger.error(f"获取欧美市场指数失败: {e}")
            return {"error": str(e)}
