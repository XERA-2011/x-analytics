"""
AI 产业链火热度与周期监测模块
"""

import akshare as ak
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.us_spot_helper import get_us_spot_direct
from ...core.data_provider import data_provider
from ...core.logger import logger


class AIOverview:
    """AI 产业链热度与周期分析"""

    # AI 产业链代表性美股列表
    US_AI_SYMBOLS = [
        "NVDA", "AMD", "AVGO", "MU", "MSFT", 
        "GOOGL", "AMZN", "META", "SMCI", "VRT", 
        "PLTR", "SOXX"
    ]

    @staticmethod
    @cached(
        "ai:overview", 
        ttl=settings.CACHE_TTL["market_heat"], 
        stale_ttl=settings.CACHE_TTL["market_heat"] * settings.STALE_TTL_RATIO
    )
    def get_overview() -> Dict[str, Any]:
        """
        获取 AI 产业链 6 层明细、综合热度得分及周期阶段判断
        """
        try:
            logger.info("🤖 开始获取与计算 AI 产业链数据...")
            
            # 1. 极速获取美股 AI 核心标的行情
            spot_map = get_us_spot_direct(AIOverview.US_AI_SYMBOLS)
            
            # 2. 准备美股标的数据对象辅助获取函数
            def get_stock(symbol: str, default_name: str) -> Dict[str, Any]:
                if symbol in spot_map:
                    item = spot_map[symbol]
                    return {
                        "symbol": symbol,
                        "name": default_name,
                        "price": item["price"],
                        "change_pct": item["change_pct"]
                    }
                return {
                    "symbol": symbol,
                    "name": default_name,
                    "price": None,
                    "change_pct": 0.0
                }

            # 各代表标的行情
            nvda = get_stock("NVDA", "英伟达")
            amd = get_stock("AMD", "AMD")
            avgo = get_stock("AVGO", "博通")
            mu = get_stock("MU", "美光科技")
            msft = get_stock("MSFT", "微软")
            googl = get_stock("GOOGL", "谷歌")
            amzn = get_stock("AMZN", "亚马逊")
            meta = get_stock("META", "Meta")
            smci = get_stock("SMCI", "超微电脑")
            vrt = get_stock("VRT", "维谛技术")
            pltr = get_stock("PLTR", "Palantir")
            soxx = get_stock("SOXX", "费半半导体ETF")

            # 3. 获取 A股 AI 板块表现作为补充与 L6 投机情绪衡量
            cn_ai_sectors = []
            try:
                board_df = data_provider.get_board_industry_name()
                if not board_df.empty:
                    # 查找 A股 AI 关键板块
                    target_boards = ["半导体", "电子元件", "通信设备", "计算机设备", "软件开发"]
                    matched = board_df[board_df["板块名称"].isin(target_boards)]
                    for _, row in matched.iterrows():
                        cn_ai_sectors.append({
                            "name": row["板块名称"],
                            "change_pct": safe_float(row["涨跌幅"]),
                            "top_stock": str(row.get("领涨股票", "")),
                            "top_stock_pct": safe_float(row.get("领涨股票-涨跌幅"))
                        })
            except Exception as e:
                logger.warning(f"⚠️ A股 AI 关联板块拉取失败: {e}")

            # 4. 构建 AI 产业链 6 层数据结构
            # Layer 1: AI 算力芯片 (最核心温度计 ★★★★★)
            l1_stocks = [nvda, amd, avgo, soxx]
            l1_avg_change = sum(s["change_pct"] for s in l1_stocks) / len(l1_stocks) if l1_stocks else 0.0

            # Layer 2: AI 存储芯片 (HBM/真实需求 ★★★★★)
            l2_stocks = [mu]
            l2_avg_change = mu["change_pct"]

            # Layer 3: 数据中心与基础设施 (服务器/制冷/网络 ★★★★☆)
            l3_stocks = [smci, vrt]
            l3_avg_change = sum(s["change_pct"] for s in l3_stocks) / len(l3_stocks) if l3_stocks else 0.0

            # Layer 4: 云计算四大巨头 (AI CapEx ★★★★☆)
            l4_stocks = [msft, googl, amzn, meta]
            l4_avg_change = sum(s["change_pct"] for s in l4_stocks) / len(l4_stocks) if l4_stocks else 0.0

            # Layer 5: AI 软件与 Agent 应用 (商业化落地 ★★★☆☆)
            l5_stocks = [pltr]
            l5_avg_change = pltr["change_pct"]

            # Layer 6: AI 概念情绪 (A股与小票 ★)
            l6_avg_change = sum(s["change_pct"] for s in cn_ai_sectors) / len(cn_ai_sectors) if cn_ai_sectors else 0.0

            layers = [
                {
                    "layer_id": "L1",
                    "title": "第一层：AI 算力芯片",
                    "star": "★★★★★",
                    "importance": "核心温度计",
                    "avg_change": round(l1_avg_change, 2),
                    "items": l1_stocks,
                    "desc": "包含 NVDA、AMD、博通及费城半导体 ETF，直接决定 AI 资金总风向。"
                },
                {
                    "layer_id": "L2",
                    "title": "第二层：AI 存储芯片 (HBM)",
                    "star": "★★★★★",
                    "importance": "真实需求验证",
                    "avg_change": round(l2_avg_change, 2),
                    "items": l2_stocks,
                    "desc": "包含美光科技 (HBM/DRAM)，验证算力需求是否成功传导至高带宽存储。"
                },
                {
                    "layer_id": "L3",
                    "title": "第三层：数据中心与基础设施",
                    "star": "★★★★☆",
                    "importance": "基建开支落地",
                    "avg_change": round(l3_avg_change, 2),
                    "items": l3_stocks,
                    "desc": "包含超微电脑 (服务器)、维谛技术 (液冷电源)，反映真实硬件建设开支。"
                },
                {
                    "layer_id": "L4",
                    "title": "第四层：云计算四大巨头",
                    "star": "★★★★☆",
                    "importance": "CapEx 资本开支",
                    "avg_change": round(l4_avg_change, 2),
                    "items": l4_stocks,
                    "desc": "微软、谷歌、亚马逊、Meta，其 AI 资本开支决定产业链向上繁荣上限。"
                },
                {
                    "layer_id": "L5",
                    "title": "第五层：AI 软件与应用",
                    "star": "★★★☆☆",
                    "importance": "商业化与渗透",
                    "avg_change": round(l5_avg_change, 2),
                    "items": l5_stocks,
                    "desc": "以 Palantir 为代表的 AI Agent 及 Enterprise SaaS 应用层。"
                },
                {
                    "layer_id": "L6",
                    "title": "第六层：A股/边缘 AI 概念",
                    "star": "★☆☆☆☆",
                    "importance": "泡沫投机指示",
                    "avg_change": round(l6_avg_change, 2),
                    "items": cn_ai_sectors[:4],
                    "desc": "A股半导体与 AI 板块题材，若边缘小票狂热暴涨往往预示情绪高潮近尾声。"
                }
            ]

            # 5. 计算 AI 综合热度得分 (AI Heat Score, 0~100)
            # 基础分为 50 分，根据各层变动按权重加权增减
            weighted_pct = (
                l1_avg_change * 0.35 +
                l2_avg_change * 0.25 +
                l3_avg_change * 0.20 +
                l4_avg_change * 0.15 +
                l5_avg_change * 0.05
            )
            # 动量系数 mapped to 0-100
            heat_score = min(100.0, max(0.0, 50.0 + weighted_pct * 8.0))
            heat_score = round(heat_score, 1)

            # 6. 周期阶段判定 (Cycle Phase Assessment)
            if nvda["change_pct"] > 1.0 and l2_avg_change > 0.5 and l3_avg_change > 0.5:
                cycle_phase = "硬件爆发扩张期"
                cycle_status = "active"
                cycle_desc = "算力芯片与存储 HBM、数据中心基础设施强劲共振，产业处于资本扩张牛市阶段。"
            elif nvda["change_pct"] <= 0 and l6_avg_change > 2.0:
                cycle_phase = "情绪过热 / 泡沫预警"
                cycle_status = "warning"
                cycle_desc = "龙头芯片高位回落，资金向边缘概念小票过度扩散，需警惕短期估值泡沫与情绪见顶风险。"
            elif nvda["change_pct"] < -2.0 and l4_avg_change < -1.5:
                cycle_phase = "周期回调降温期"
                cycle_status = "cooling"
                cycle_desc = "芯片与云巨头资本开支情绪同步回落，市场进入阶段性消化与降温期。"
            else:
                cycle_phase = "稳健消化期"
                cycle_status = "neutral"
                cycle_desc = "AI 产业链各环节涨跌分化，市场在高基数下消化估值，等待新的业绩催化。"

            # 7. 三大关键监控信号 (Key Signals)
            signals = [
                {
                    "title": "信号1：算力龙头动向",
                    "status": "看多" if nvda["change_pct"] >= 0 else "走弱",
                    "status_class": "up" if nvda["change_pct"] >= 0 else "down",
                    "desc": f"英伟达 NVDA ({nvda['change_pct']:+.2f}%) 与费半 SOXX ({soxx['change_pct']:+.2f}%)"
                },
                {
                    "title": "信号2：存储 HBM 传导",
                    "status": "强劲" if mu["change_pct"] >= 0 else "偏弱",
                    "status_class": "up" if mu["change_pct"] >= 0 else "down",
                    "desc": f"美光科技 MU ({mu['change_pct']:+.2f}%) 验证高带宽存储真实需求"
                },
                {
                    "title": "信号3：云巨头 CapEx 支撑",
                    "status": "稳定" if l4_avg_change >= -0.5 else "压力",
                    "status_class": "up" if l4_avg_change >= -0.5 else "down",
                    "desc": f"微软/谷歌/亚马逊/Meta 4大巨头平均变动 ({l4_avg_change:+.2f}%)"
                }
            ]

            return {
                "update_time": get_beijing_time(),
                "heat_score": heat_score,
                "cycle_phase": cycle_phase,
                "cycle_status": cycle_status,
                "cycle_desc": cycle_desc,
                "signals": signals,
                "layers": layers
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 AI 产业链数据失败: {e}", exc_info=True)
            return {"error": f"获取 AI 产业链数据失败: {str(e)}"}
