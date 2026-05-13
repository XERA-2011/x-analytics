"""
美国市场领涨领跌分析
"""

import akshare as ak
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class USMarketLeaders:
    """美国市场主要指数与领涨板块分析"""

    @staticmethod
    @cached("market_us:indices", ttl=settings.CACHE_TTL["market_heat"], stale_ttl=settings.CACHE_TTL["market_heat"] * settings.STALE_TTL_RATIO)
    def get_leaders() -> Dict[str, Any]:
        """
        获取美国市场三大指数 (纳斯达克, 标普500, 道琼斯)
        """
        indices_data = []
        
        # 定义指数代码
        indices_map = [
            {"name": "纳斯达克", "code": ".IXIC"},
            {"name": "标普500", "code": ".INX"},
            {"name": "道琼斯", "code": ".DJI"}
        ]

        try:
            logger.info("📊 获取美国市场主要指数...")
            
            for item in indices_map:
                try:
                    df = akshare_call_with_retry(ak.index_us_stock_sina, symbol=item["code"])
                    if not df.empty and len(df) >= 2:
                        # 获取最新和前一日数据
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        current_price = safe_float(latest["close"])
                        prev_close = safe_float(prev["close"])
                        
                        # 确保价格数据有效
                        if current_price is None or prev_close is None or prev_close == 0:
                            logger.warning(f"⚠️ 指数 {item['name']} 价格数据无效，跳过")
                            continue
                        
                        change_amount = current_price - prev_close
                        change_pct = change_amount / prev_close * 100
                            
                        indices_data.append({
                            "name": item["name"],
                            "code": item["code"],
                            "price": current_price,
                            "change_amount": change_amount,
                            "change_pct": change_pct
                        })
                    else:
                        # 数据不足，跳过该指数（不填充假数据）
                        logger.warning(f"⚠️ 指数 {item['name']} 数据不足，跳过")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ 获取指数 {item['name']} 失败: {e}")
                    # 跳过失败的指数，不填充假数据
                    continue

            core_index_count = sum(1 for item in indices_data if item.get("code") in {".IXIC", ".INX", ".DJI"})
            if core_index_count != len(indices_map):
                logger.error("❌ 美国核心指数数据不完整: expected=%s actual=%s", len(indices_map), core_index_count)
                return {"error": "美国核心指数数据不完整"}

            # 添加中概股 (使用 PGJ ETF 作为代理 - Invesco Golden Dragon China ETF)
            try:
                # 使用 stock_us_daily (Sina源) 获取 PGJ 数据，避开 EM 接口屏蔽
                df_cne = akshare_call_with_retry(ak.stock_us_daily, symbol='PGJ', adjust="qfq")
                if not df_cne.empty and len(df_cne) >= 2:
                    latest = df_cne.iloc[-1]
                    prev = df_cne.iloc[-2]
                    
                    current_price = safe_float(latest["close"])
                    prev_close = safe_float(prev["close"])
                    
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

            # 如果全部失败，返回错误而非假数据
            if not indices_data:
                 logger.error("❌ 所有美国指数数据获取失败")
                 return {"error": "无法获取美国指数实时数据"}

            return {
                "indices": indices_data,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            logger.error(f" 获取美国市场指数失败: {e}")
            return {"error": str(e)}
