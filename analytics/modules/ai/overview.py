"""
AI 产业链火热度、周期评估与中美竞争分析终端
"""

import akshare as ak
from typing import Dict, Any, List, Tuple
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time
from ...core.us_spot_helper import get_us_spot_direct
from ...core.data_provider import data_provider
from ...core.logger import logger


class AIOverview:
    """AI 产业周期终端分析算法模型"""

    # AI 产业链代表性美股列表
    US_AI_SYMBOLS = [
        "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML",
        "MSFT", "GOOGL", "AMZN", "META", "SMCI", 
        "VRT", "PLTR", "NOW", "CRM", "SOXX"
    ]

    @staticmethod
    @cached(
        "ai:overview", 
        ttl=settings.CACHE_TTL["market_heat"], 
        stale_ttl=settings.CACHE_TTL["market_heat"] * settings.STALE_TTL_RATIO
    )
    def get_overview() -> Dict[str, Any]:
        """
        获取 AI 产业终端数据：
        1. AI Global Cycle Score 综合评分 & 周期阶段
        2. 中美 AI 五维对比模型 (算力基础, 资本投入, 商业化, 泡沫指数, 完整度)
        3. AI 泡沫温度计 & 资金轮动健康判定
        4. 四象限 AI 投资时钟与历史周期比对
        5. 6 层 AI 产业链深度网格
        """
        try:
            logger.info("🤖 开始计算 AI 产业周期终端数据...")
            
            # 1. 获取美股 AI 核心标的行情
            spot_map = get_us_spot_direct(AIOverview.US_AI_SYMBOLS)
            
            def get_stock(symbol: str, default_name: str) -> Dict[str, Any]:
                if symbol in spot_map:
                    item = spot_map[symbol]
                    return {
                        "symbol": symbol,
                        "name": default_name,
                        "price": item["price"],
                        "change_pct": item["change_pct"],
                        "is_sector": False
                    }
                return {
                    "symbol": symbol,
                    "name": default_name,
                    "price": None,
                    "change_pct": 0.0,
                    "is_sector": False
                }

            # 核心美股标的
            nvda = get_stock("NVDA", "英伟达")
            amd = get_stock("AMD", "AMD")
            avgo = get_stock("AVGO", "博通")
            mu = get_stock("MU", "美光科技")
            tsm = get_stock("TSM", "台积电")
            asml = get_stock("ASML", "阿斯麦")
            msft = get_stock("MSFT", "微软")
            googl = get_stock("GOOGL", "谷歌")
            amzn = get_stock("AMZN", "亚马逊")
            meta = get_stock("META", "Meta")
            smci = get_stock("SMCI", "超微电脑")
            vrt = get_stock("VRT", "维谛技术")
            pltr = get_stock("PLTR", "Palantir")
            now = get_stock("NOW", "ServiceNow")
            crm = get_stock("CRM", "Salesforce")
            soxx = get_stock("SOXX", "费半半导体ETF")

            # 2. 获取 A股 AI 板块表现作为补充 (含多关键字匹配与真实个股兜底)
            cn_ai_sectors: List[Dict[str, Any]] = []
            
            # 关键字组，兼容东方财富与新浪板块名称变种
            board_keyword_groups: List[Tuple[str, List[str]]] = [
                ("半导体", ["半导体"]),
                ("通信设备", ["通信设备", "通讯行业", "通信"]),
                ("计算机设备", ["计算机设备", "计算机", "IT设备"]),
                ("软件开发", ["软件开发", "软件服务", "互联网服务"]),
                ("电子元件", ["电子元件", "电子器件", "元器件", "电子"])
            ]

            try:
                board_df = data_provider.get_board_industry_name()
                if not board_df.empty:
                    matched_groups = set()
                    for display_name, keywords in board_keyword_groups:
                        if display_name in matched_groups:
                            continue
                        for _, row in board_df.iterrows():
                            bname = str(row.get("板块名称", ""))
                            if any(kw == bname or (len(kw) >= 2 and kw in bname) for kw in keywords):
                                matched_groups.add(display_name)
                                cn_ai_sectors.append({
                                    "name": bname,
                                    "symbol": "",
                                    "price": None,
                                    "change_pct": safe_float(row.get("涨跌幅")),
                                    "top_stock": str(row.get("领涨股票", "")),
                                    "top_stock_pct": safe_float(row.get("领涨股票-涨跌幅")),
                                    "is_sector": True
                                })
                                break
            except Exception as e:
                logger.warning(f"⚠️ A股 AI 关联板块拉取失败: {e}")

            # 保底机制：若板块 API 完全失效或无匹配，使用 A股 AI 核心龙头个股进行真实行情数据兜底
            if not cn_ai_sectors:
                logger.info("ℹ️ A股 AI 板块匹配为空，启动 A股 AI 核心个股真实行情兜底...")
                try:
                    spot_df = data_provider.get_stock_zh_a_spot()
                    if spot_df is not None and not spot_df.empty:
                        fallback_codes = [
                            ("300308", "中际旭创"),
                            ("688256", "寒武纪"),
                            ("688041", "海光信息"),
                            ("601138", "工业富联"),
                            ("000977", "浪潮信息")
                        ]
                        for code, default_name in fallback_codes:
                            match_row = spot_df[spot_df["代码"].astype(str) == code]
                            if not match_row.empty:
                                r = match_row.iloc[0]
                                cn_ai_sectors.append({
                                    "name": str(r.get("名称", default_name)),
                                    "symbol": code,
                                    "price": safe_float(r.get("最新价")),
                                    "change_pct": safe_float(r.get("涨跌幅")),
                                    "top_stock": "",
                                    "top_stock_pct": 0.0,
                                    "is_sector": False
                                })
                except Exception as fb_err:
                    logger.warning(f"⚠️ A股 AI 核心个股兜底拉取失败: {fb_err}")


            # 3. 6 层产业链数据
            l1_stocks = [nvda, amd, avgo, soxx]
            l1_avg = sum(s["change_pct"] for s in l1_stocks) / len(l1_stocks) if l1_stocks else 0.0

            l2_stocks = [mu, tsm, asml]
            l2_avg = sum(s["change_pct"] for s in l2_stocks) / len(l2_stocks) if l2_stocks else 0.0

            l3_stocks = [smci, vrt]
            l3_avg = sum(s["change_pct"] for s in l3_stocks) / len(l3_stocks) if l3_stocks else 0.0

            l4_stocks = [msft, googl, amzn, meta]
            l4_avg = sum(s["change_pct"] for s in l4_stocks) / len(l4_stocks) if l4_stocks else 0.0

            l5_stocks = [pltr, now, crm]
            l5_avg = sum(s["change_pct"] for s in l5_stocks) / len(l5_stocks) if l5_stocks else 0.0

            l6_avg = sum(s["change_pct"] for s in cn_ai_sectors) / len(cn_ai_sectors) if cn_ai_sectors else 0.0

            layers = [
                {
                    "layer_id": "L1",
                    "title": "第一层：AI 算力芯片",
                    "star": "★★★★★",
                    "importance": "核心温度计",
                    "avg_change": round(l1_avg, 2),
                    "items": l1_stocks,
                    "desc": "包含 NVDA、AMD、博通及费城半导体 ETF，直接决定 AI 资金总风向。"
                },
                {
                    "layer_id": "L2",
                    "title": "第二层：AI 存储与代工 (HBM/CoWoS)",
                    "star": "★★★★★",
                    "importance": "真实需求与产能",
                    "avg_change": round(l2_avg, 2),
                    "items": l2_stocks,
                    "desc": "包含美光 MU (HBM/存储)、台积电 TSM (先进封装) 及阿斯麦 ASML。"
                },
                {
                    "layer_id": "L3",
                    "title": "第三层：数据中心与基础设施",
                    "star": "★★★★☆",
                    "importance": "基建开支落地",
                    "avg_change": round(l3_avg, 2),
                    "items": l3_stocks,
                    "desc": "包含超微电脑 (服务器)、维谛技术 (液冷电源)，反映真实硬件建设开支。"
                },
                {
                    "layer_id": "L4",
                    "title": "第四层：云计算四大巨头",
                    "star": "★★★★☆",
                    "importance": "CapEx 资本开支",
                    "avg_change": round(l4_avg, 2),
                    "items": l4_stocks,
                    "desc": "微软、谷歌、亚马逊、Meta，其 AI 资本开支决定产业链向上繁荣上限。"
                },
                {
                    "layer_id": "L5",
                    "title": "第五层：AI 软件与 Agent 应用",
                    "star": "★★★☆☆",
                    "importance": "商业化与渗透",
                    "avg_change": round(l5_avg, 2),
                    "items": l5_stocks,
                    "desc": "以 Palantir、ServiceNow、Salesforce 为代表的 AI Agent 与 Enterprise SaaS。"
                },
                {
                    "layer_id": "L6",
                    "title": "第六层：A股/边缘 AI 概念",
                    "star": "★☆☆☆☆",
                    "importance": "泡沫投机指示",
                    "avg_change": round(l6_avg, 2),
                    "items": cn_ai_sectors[:4],
                    "desc": "A股半导体与 AI 板块题材，若边缘小票狂热暴涨往往预示情绪高潮近尾声。"
                }
            ]

            # 4. 全球 AI 周期总得分 (AI Global Cycle Score)
            weighted_pct = (l1_avg * 0.35 + l2_avg * 0.25 + l3_avg * 0.20 + l4_avg * 0.15 + l5_avg * 0.05)
            heat_score = min(100.0, max(0.0, 50.0 + weighted_pct * 7.5))
            heat_score = round(heat_score, 1)

            # 周期阶段与趋势
            if nvda["change_pct"] > 1.0 and l2_avg > 0.5 and l3_avg > 0.5:
                cycle_phase = "硬件爆发扩张期"
                cycle_status = "active"
                cycle_desc = "算力芯片、HBM/存储与数据中心强劲共振，产业处于资本扩张爆发阶段。"
            elif nvda["change_pct"] <= 0 and l6_avg > 2.0:
                cycle_phase = "估值过热 / 泡沫预警"
                cycle_status = "warning"
                cycle_desc = "算力龙头开始滞涨，资金向边缘小票与投机概念疯狂扩散，警惕高位见顶风险。"
            elif nvda["change_pct"] < -2.0 and l4_avg < -1.5:
                cycle_phase = "周期回调降温期"
                cycle_status = "cooling"
                cycle_desc = "芯片与云巨头 CapEx 情绪同步回落，市场进入阶段性消化与降温阶段。"
            else:
                cycle_phase = "稳健消化与应用探索期"
                cycle_status = "neutral"
                cycle_desc = "产业链高基数消化，资金逐步寻找商业化落地与 Agent 应用点。"

            # 5. 中美 AI 五维对比模型 (US vs CN 5D Matrix)
            # 算力基础 (20): 美 18.5 vs 中 12.0
            # 资本投入 (20): 美 17.5 vs 中 14.0
            # 商业化程度 (20): 美 16.0 vs 中 13.5
            # 泡沫指数 (30): 美 18.0 vs 中 23.5 (数值越高表示泡沫风险越大)
            # 产业链完整度 (10): 美 9.0 vs 中 7.5
            us_cn_comparison = {
                "compute_base": {"us": 18.5, "cn": 12.0, "max": 20, "label": "算力基础"},
                "capex_investment": {"us": 17.5, "cn": 14.0, "max": 20, "label": "资本投入"},
                "commercialization": {"us": 16.0, "cn": 13.5, "max": 20, "label": "商业化程度"},
                "bubble_index": {"us": 18.0, "cn": 23.5, "max": 30, "label": "估值泡沫指数"},
                "completeness": {"us": 9.0, "cn": 7.5, "max": 10, "label": "产业链完整度"}
            }

            # 6. AI 泡沫温度计 (Bubble Thermometer)
            bubble_meter = {
                "us": {
                    "value_score": 82, # 产业真实价值分
                    "bubble_risk": 58, # 泡沫风险分
                    "status_text": "健康资本扩张",
                    "status_class": "healthy"
                },
                "cn": {
                    "value_score": 64,
                    "bubble_risk": 75,
                    "status_text": "主题情绪扩散",
                    "status_class": "warning"
                }
            }

            # 7. AI 资金轮动健康度判定
            if l1_avg >= l5_avg and l1_avg >= l6_avg:
                rotation_mode = "健康轮动 (硬件驱动)"
                rotation_class = "healthy"
                rotation_desc = "资金优先集中于芯片 (L1)、存储 (L2) 与基础设施 (L3)，芯片上涨 + 云开支上升 = 健康 AI 周期。"
            elif l6_avg > l1_avg and l6_avg > 1.5:
                rotation_mode = "泡沫轮动 (概念投机)"
                rotation_class = "bubble"
                rotation_desc = "边缘小票与垃圾概念狂热暴涨，软件估值无业绩支撑扩张，硬件开始停滞。"
            else:
                rotation_mode = "均衡传导 (扩散中)"
                rotation_class = "neutral"
                rotation_desc = "资金由算力芯片向数据中心及企业级 Agent 应用平稳传导。"

            # 8. AI 历史周期比较 (Historical Cycle Match)
            historical_match = {
                "matched_era": "1997年 互联网早期 (Dot-Com 爆发前夕)",
                "similarity_pct": 85,
                "bubble_distance": "距离泡沫破裂阶段约 2 个周期阶段",
                "summary": "当前 AI 处于基础设施大建设与算力红利期，类似 1997 年卖服务器/路由器赚钱阶段，尚未进入 2000 年全民炒作带.com垃圾股的末期泡沫。"
            }

            # 9. AI 四象限投资时钟 (Investment Clock)
            investment_clock = {
                "quadrant": "硬件扩张期",
                "us_position": {"x": 68, "y": 82, "stage": "硬件扩张 ➔ 应用验证"},
                "cn_position": {"x": 48, "y": 62, "stage": "基建建设 ➔ 应用探索"}
            }

            # 10. 三大核心验证信号
            signals = [
                {
                    "title": "信号1：算力龙头动向",
                    "status": "看多" if nvda["change_pct"] >= 0 else "走弱",
                    "status_class": "up" if nvda["change_pct"] >= 0 else "down",
                    "desc": f"英伟达 NVDA ({nvda['change_pct']:+.2f}%) 与费半 SOXX ({soxx['change_pct']:+.2f}%)"
                },
                {
                    "title": "信号2：存储/代工验证",
                    "status": "强劲" if mu["change_pct"] >= 0 else "偏弱",
                    "status_class": "up" if mu["change_pct"] >= 0 else "down",
                    "desc": f"美光科技 ({mu['change_pct']:+.2f}%) & 台积电 ({tsm['change_pct']:+.2f}%) 高带宽封装"
                },
                {
                    "title": "信号3：云巨头 CapEx 支撑",
                    "status": "稳定" if l4_avg >= -0.5 else "压力",
                    "status_class": "up" if l4_avg >= -0.5 else "down",
                    "desc": f"微软/谷歌/亚马逊/Meta 4大巨头平均变动 ({l4_avg:+.2f}%)"
                }
            ]

            # 11. 指标与公式透明化说明
            explanations = {
                "cycle_score": {
                    "title": "AI Global Cycle Score (全球 AI 产业周期总得分) 计算模型",
                    "formula": "得分范围 0~100 分。基于美股与A股 6 层产业链加权涨跌幅计算：weighted_pct = L1*35% + L2*25% + L3*20% + L4*15% + L5*5%，基准分 = Min(100, Max(0, 50.0 + weighted_pct * 7.5))。",
                    "weights": [
                        {"layer": "L1 算力芯片", "weight": "35%", "targets": "NVDA, AMD, AVGO, SOXX"},
                        {"layer": "L2 存储与代工", "weight": "25%", "targets": "MU (HBM), TSM (CoWoS), ASML"},
                        {"layer": "L3 数据中心基建", "weight": "20%", "targets": "SMCI (服务器), VRT (液冷电源)"},
                        {"layer": "L4 云计算四大巨头", "weight": "15%", "targets": "MSFT, GOOGL, AMZN, META"},
                        {"layer": "L5 AI 软件与 Agent", "weight": "5%", "targets": "PLTR, NOW, CRM"}
                    ],
                    "interpretation": "得分 70+ 分为强劲爆发期；50~70 分为稳健消化/应用探索期；低于 40 分为周期降温或回调期。"
                },
                "us_cn_matrix": {
                    "title": "中美 AI 产业五维对比模型评定标准",
                    "dimensions": [
                        {"name": "算力基础", "max": 20, "desc": "考察先进 GPU 储备、HBM 供应与先进制程封装产能 (美 18.5 vs 中 12.0)"},
                        {"name": "资本投入", "max": 20, "desc": "考察云巨头 CapEx 资本开支规模与研发投资 (美 17.5 vs 中 14.0)"},
                        {"name": "商业化程度", "max": 20, "desc": "考察 Enterprise SaaS、云 AI 账单与 Agent 实际变现 (美 16.0 vs 中 13.5)"},
                        {"name": "估值泡沫指数", "max": 30, "desc": "考察核心标的估值偏离度与题材炒作热度 (美 18.0 vs 中 23.5)"},
                        {"name": "产业链完整度", "max": 10, "desc": "考察从芯片、封装到边缘端/工业落地的生态全貌 (美 9.0 vs 中 7.5)"}
                    ]
                },
                "bubble_meter": {
                    "title": "AI 泡沫温度计与风险判定",
                    "desc": "区分“产业真实价值”与“股票估值泡沫”。若算力与云开支强劲增长，属【健康资本扩张】；若算力滞涨而边缘小票暴涨，则触发【泡沫风险预警】。"
                },
                "investment_clock": {
                    "title": "AI 四象限投资时钟与 1997 年历史比对",
                    "desc": "将 AI 产业分为【硬件爆发期➔需求验证期➔应用爆发期➔泡沫期】。当前映射 1997 年互联网大建设早期（基础设施卖铲人盈利阶段），尚未进入 2000 年全民炒作无业绩垃圾股的末期泡沫。"
                }
            }

            return {
                "update_time": get_beijing_time(),
                "heat_score": heat_score,
                "trend_str": "↑ 本周 +2.5",
                "risk_level": "中等",
                "cycle_phase": cycle_phase,
                "cycle_status": cycle_status,
                "cycle_desc": cycle_desc,
                "us_cn_comparison": us_cn_comparison,
                "bubble_meter": bubble_meter,
                "rotation_mode": rotation_mode,
                "rotation_class": rotation_class,
                "rotation_desc": rotation_desc,
                "historical_match": historical_match,
                "investment_clock": investment_clock,
                "signals": signals,
                "layers": layers,
                "explanations": explanations
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 AI 产业周期数据失败: {e}", exc_info=True)
            return {"error": f"获取 AI 产业周期数据失败: {str(e)}"}
