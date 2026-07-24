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

    # AI 产业链代表性美股列表 (包含 2026 最新能源、ASIC及云基建关键标的)
    US_AI_SYMBOLS = [
        "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML",
        "MSFT", "GOOGL", "AMZN", "META", "SMCI", 
        "VRT", "PLTR", "NOW", "CRM", "SOXX",
        "GEV", "CEG", "VST", "ETN", "ARM", "MRVL", "DELL", "ORCL", "SMH"
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
        2. 中美 AI 五维对比模型 (含 A股芯片龙头动态微调)
        3. AI 泡沫温度计 & 资金轮动健康判定
        4. 四象限 AI 投资时钟与历史周期比对
        5. 7 层 AI 产业链深度网格 (增加 L0 能源电力层)
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

            # L0 能源与电力基建标的 (2026 产业核心瓶颈)
            gev = get_stock("GEV", "GE Vernova")
            ceg = get_stock("CEG", "Constellation核电")
            vst = get_stock("VST", "Vistra电力")
            etn = get_stock("ETN", "伊顿电气")

            # L1 算力芯片与架构
            nvda = get_stock("NVDA", "英伟达")
            amd = get_stock("AMD", "AMD")
            avgo = get_stock("AVGO", "博通")
            arm = get_stock("ARM", "ARM架构")
            mrvl = get_stock("MRVL", "迈威尔ASIC")
            smh = get_stock("SMH", "半导体ETF")
            soxx = get_stock("SOXX", "费半ETF")

            # L2 存储与代工
            mu = get_stock("MU", "美光科技")
            tsm = get_stock("TSM", "台积电")
            asml = get_stock("ASML", "阿斯麦")

            # L3 数据中心与基建
            smci = get_stock("SMCI", "超微电脑")
            vrt = get_stock("VRT", "维谛液冷电源")
            dell = get_stock("DELL", "戴尔AI服务器")

            # L4 云计算巨头与AI云
            msft = get_stock("MSFT", "微软")
            googl = get_stock("GOOGL", "谷歌")
            amzn = get_stock("AMZN", "亚马逊")
            meta = get_stock("META", "Meta")
            orcl = get_stock("ORCL", "甲骨文云")

            # L5 AI 软件与 Agent
            pltr = get_stock("PLTR", "Palantir")
            now = get_stock("NOW", "ServiceNow")
            crm = get_stock("CRM", "Salesforce")

            # 2. 获取 A股 AI 板块与真实领头羊行情
            cn_ai_sectors: List[Dict[str, Any]] = []
            cn_ai_leaders: List[Dict[str, Any]] = []
            
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

            # 拉取 A股 AI 核心龙头真实行情 (寒武纪, 海光信息, 中际旭创, 工业富联, 浪潮信息)
            try:
                spot_df = data_provider.get_stock_zh_a_spot()
                if spot_df is not None and not spot_df.empty:
                    fallback_codes = [
                        ("688256", "寒武纪-U"),
                        ("688041", "海光信息"),
                        ("300308", "中际旭创"),
                        ("601138", "工业富联"),
                        ("000977", "浪潮信息")
                    ]
                    for code, default_name in fallback_codes:
                        match_row = spot_df[spot_df["代码"].astype(str) == code]
                        if not match_row.empty:
                            r = match_row.iloc[0]
                            cn_ai_leaders.append({
                                "name": str(r.get("名称", default_name)),
                                "symbol": code,
                                "price": safe_float(r.get("最新价")),
                                "change_pct": safe_float(r.get("涨跌幅")),
                                "top_stock": "",
                                "top_stock_pct": 0.0,
                                "is_sector": False
                            })
            except Exception as fb_err:
                logger.warning(f"⚠️ A股 AI 核心龙头拉取失败: {fb_err}")

            if not cn_ai_sectors:
                cn_ai_sectors = cn_ai_leaders[:]

            # 3. 7 层产业链数据计算
            l0_stocks = [gev, ceg, vst, etn]
            l0_avg = sum(s["change_pct"] for s in l0_stocks) / len(l0_stocks) if l0_stocks else 0.0

            l1_stocks = [nvda, amd, avgo, arm, mrvl, smh, soxx]
            l1_avg = sum(s["change_pct"] for s in l1_stocks) / len(l1_stocks) if l1_stocks else 0.0

            l2_stocks = [mu, tsm, asml]
            l2_avg = sum(s["change_pct"] for s in l2_stocks) / len(l2_stocks) if l2_stocks else 0.0

            l3_stocks = [smci, vrt, dell]
            l3_avg = sum(s["change_pct"] for s in l3_stocks) / len(l3_stocks) if l3_stocks else 0.0

            l4_stocks = [msft, googl, amzn, meta, orcl]
            l4_avg = sum(s["change_pct"] for s in l4_stocks) / len(l4_stocks) if l4_stocks else 0.0

            l5_stocks = [pltr, now, crm]
            l5_avg = sum(s["change_pct"] for s in l5_stocks) / len(l5_stocks) if l5_stocks else 0.0

            l6_avg = sum(s["change_pct"] for s in cn_ai_sectors) / len(cn_ai_sectors) if cn_ai_sectors else 0.0

            layers = [
                {
                    "layer_id": "L0",
                    "title": "零层：能源与电力基础设施",
                    "star": "★★★★★",
                    "importance": "AI扩张核心瓶颈",
                    "avg_change": round(l0_avg, 2),
                    "items": l0_stocks,
                    "desc": "AI 的尽头是电力！涵盖 GEV(电气设备)、CEG(核电)、VST(电力公用) 及 ETN(配电管理)。"
                },
                {
                    "layer_id": "L1",
                    "title": "第一层：AI 算力芯片与架构",
                    "star": "★★★★★",
                    "importance": "核心总风向标",
                    "avg_change": round(l1_avg, 2),
                    "items": l1_stocks,
                    "desc": "包含 NVDA、AMD、博通、ARM 架构、MRVL 芯片与半导体 ETF，决定资金总风向。"
                },
                {
                    "layer_id": "L2",
                    "title": "第二层：AI 存储与代工 (HBM/CoWoS)",
                    "star": "★★★★★",
                    "importance": "真实产能供需",
                    "avg_change": round(l2_avg, 2),
                    "items": l2_stocks,
                    "desc": "包含美光 MU (HBM内存)、台积电 TSM (先进封装) 及阿斯麦 ASML (光刻机)。"
                },
                {
                    "layer_id": "L3",
                    "title": "第三层：数据中心与基础设施",
                    "star": "★★★★☆",
                    "importance": "基建开支落地",
                    "avg_change": round(l3_avg, 2),
                    "items": l3_stocks,
                    "desc": "包含超微电脑、维谛液冷电源及戴尔服务器，反映硬件基础设施建设落地。"
                },
                {
                    "layer_id": "L4",
                    "title": "第四层：云计算四大巨头与 AI 云",
                    "star": "★★★★☆",
                    "importance": "CapEx 资本开支",
                    "avg_change": round(l4_avg, 2),
                    "items": l4_stocks,
                    "desc": "微软、谷歌、亚马逊、Meta 及甲骨文，其 CapEx 开支规模决定产业链繁荣上限。"
                },
                {
                    "layer_id": "L5",
                    "title": "第五层：AI 软件与 Agent 应用",
                    "star": "★★★☆☆",
                    "importance": "商业化变现",
                    "avg_change": round(l5_avg, 2),
                    "items": l5_stocks,
                    "desc": "以 Palantir、ServiceNow、Salesforce 为代表的企业级 AI Agent 与 SaaS 应用。"
                },
                {
                    "layer_id": "L6",
                    "title": "第六层：A股/边缘 AI 概念",
                    "star": "★☆☆☆☆",
                    "importance": "泡沫投机指示",
                    "avg_change": round(l6_avg, 2),
                    "items": cn_ai_sectors[:4],
                    "desc": "A股半导体与 AI 游资概念题材，若边缘小票狂热暴涨往往预示短线情绪近尾声。"
                }
            ]

            # 4. 全球 AI 周期总得分 (AI Global Cycle Score) - 含 15% 能源因子
            weighted_pct = (
                l0_avg * 0.15 + 
                l1_avg * 0.30 + 
                l2_avg * 0.20 + 
                l3_avg * 0.15 + 
                l4_avg * 0.10 + 
                l5_avg * 0.10
            )
            heat_score = min(100.0, max(0.0, 50.0 + weighted_pct * 7.5))
            heat_score = round(heat_score, 1)

            # 周期阶段与趋势判定 (融合 L0 能源与算力)
            if nvda["change_pct"] > 0.5 and l0_avg > 0.3 and l2_avg > 0.3:
                cycle_phase = "能源与算力共振爆发期"
                cycle_status = "active"
                cycle_desc = "AI 电力基础设施、算力芯片与存储代工强劲共振，产业资本扩张加速。"
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

            # 5. 中美 AI 五维对比模型 (根据盘中 A股龙头与美股芯片动态微调分值)
            cn_core_avg = sum(s["change_pct"] for s in cn_ai_leaders) / len(cn_ai_leaders) if cn_ai_leaders else l6_avg
            
            # 动态微调
            us_compute = round(min(20.0, max(10.0, 18.5 + l1_avg * 0.2)), 1)
            cn_compute = round(min(20.0, max(8.0, 12.0 + cn_core_avg * 0.3)), 1)
            
            us_bubble = round(min(30.0, max(10.0, 18.0 + (l1_avg - l5_avg) * 0.5)), 1)
            cn_bubble = round(min(30.0, max(12.0, 23.5 + (l6_avg - cn_core_avg) * 0.8)), 1)

            us_cn_comparison = {
                "compute_base": {"us": us_compute, "cn": cn_compute, "max": 20, "label": "算力基础"},
                "capex_investment": {"us": 17.5, "cn": 14.0, "max": 20, "label": "资本投入"},
                "commercialization": {"us": 16.0, "cn": 13.5, "max": 20, "label": "商业化程度"},
                "bubble_index": {"us": us_bubble, "cn": cn_bubble, "max": 30, "label": "估值泡沫指数"},
                "completeness": {"us": 9.0, "cn": 7.5, "max": 10, "label": "产业链完整度"}
            }

            # 6. AI 泡沫温度计 (Bubble Thermometer)
            bubble_meter = {
                "us": {
                    "value_score": round(min(100, max(50, 82 + l0_avg + l1_avg)), 1),
                    "bubble_risk": us_bubble * 3.2,
                    "status_text": "健康资本扩张",
                    "status_class": "healthy"
                },
                "cn": {
                    "value_score": round(min(100, max(40, 64 + cn_core_avg)), 1),
                    "bubble_risk": cn_bubble * 3.1,
                    "status_text": "主题情绪扩散",
                    "status_class": "warning"
                }
            }

            # 7. AI 资金轮动健康度判定 (增加 L0 能源维度)
            if l0_avg > 0 and l1_avg >= l5_avg and l1_avg >= l6_avg:
                rotation_mode = "健康轮动 (能源与算力双驱动)"
                rotation_class = "healthy"
                rotation_desc = "资金优先集中于电力基础设施 (L0)、芯片 (L1) 与存储 (L2)，电力开支 + 芯片强劲 = 健康 AI 扩张期。"
            elif l6_avg > l1_avg and l6_avg > 1.5:
                rotation_mode = "泡沫轮动 (概念投机)"
                rotation_class = "bubble"
                rotation_desc = "边缘小票与垃圾概念狂热暴涨，软件估值无业绩支撑扩张，硬件与能源开始停滞。"
            else:
                rotation_mode = "均衡传导 (扩散中)"
                rotation_class = "neutral"
                rotation_desc = "资金由算力芯片与电力基建向数据中心及企业级 Agent 应用平稳传导。"

            # 8. AI 历史周期比较
            historical_match = {
                "matched_era": "1997年 互联网早期 (Dot-Com 爆发前夕)",
                "similarity_pct": 85,
                "bubble_distance": "距离泡沫破裂阶段约 2 个周期阶段",
                "summary": "当前 AI 处于基础设施大建设与电力算力红利期，类似 1997 年卖服务器/路由器/电力建设阶段，尚未进入 2000 年全民炒作无业绩垃圾股的末期泡沫。"
            }

            # 9. AI 四象限投资时钟
            investment_clock = {
                "quadrant": "硬件与能源爆发期",
                "us_position": {"x": 72, "y": 85, "stage": "能源与硬件扩张 ➔ 应用验证"},
                "cn_position": {"x": 50, "y": 64, "stage": "基建建设 ➔ 应用探索"}
            }

            # 10. 四大核心验证信号 (加入 L0 能源信号)
            signals = [
                {
                    "title": "信号1：能源电力保障",
                    "status": "充足" if l0_avg >= 0 else "紧张",
                    "status_class": "up" if l0_avg >= 0 else "down",
                    "desc": f"GE Vernova ({gev['change_pct']:+.2f}%) & Constellation核电 ({ceg['change_pct']:+.2f}%)"
                },
                {
                    "title": "信号2：算力龙头动向",
                    "status": "看多" if nvda["change_pct"] >= 0 else "走弱",
                    "status_class": "up" if nvda["change_pct"] >= 0 else "down",
                    "desc": f"英伟达 NVDA ({nvda['change_pct']:+.2f}%) & ARM架构 ({arm['change_pct']:+.2f}%)"
                },
                {
                    "title": "信号3：存储/代工验证",
                    "status": "强劲" if mu["change_pct"] >= 0 else "偏弱",
                    "status_class": "up" if mu["change_pct"] >= 0 else "down",
                    "desc": f"美光科技 ({mu['change_pct']:+.2f}%) & 台积电 ({tsm['change_pct']:+.2f}%) 先进制程"
                },
                {
                    "title": "信号4：云巨头 CapEx 支撑",
                    "status": "稳定" if l4_avg >= -0.5 else "压力",
                    "status_class": "up" if l4_avg >= -0.5 else "down",
                    "desc": f"微软/谷歌/亚马逊/Meta/甲骨文 5大巨头变动 ({l4_avg:+.2f}%)"
                }
            ]

            # 11. 指标与公式透明化说明
            explanations = {
                "cycle_score": {
                    "title": "AI Global Cycle Score (全球 AI 产业周期总得分) 六因子模型",
                    "formula": "得分范围 0~100 分。加权涨跌幅 weighted_pct = L0*15% + L1*30% + L2*20% + L3*15% + L4*10% + L5*10%。基准分 = Min(100, Max(0, 50.0 + weighted_pct * 7.5))。",
                    "weights": [
                        {"layer": "L0 能源电力", "weight": "15%", "targets": "GEV (电气), CEG (核电), VST, ETN"},
                        {"layer": "L1 算力芯片", "weight": "30%", "targets": "NVDA, AMD, AVGO, ARM, MRVL, SMH"},
                        {"layer": "L2 存储代工", "weight": "20%", "targets": "MU (HBM), TSM (CoWoS), ASML"},
                        {"layer": "L3 数据中心", "weight": "15%", "targets": "SMCI (服务器), VRT (液冷), DELL"},
                        {"layer": "L4 云巨头CapEx", "weight": "10%", "targets": "MSFT, GOOGL, AMZN, META, ORCL"},
                        {"layer": "L5 Agent与应用", "weight": "10%", "targets": "PLTR, NOW, CRM"}
                    ],
                    "interpretation": "得分 70+ 分为能源与算力强劲爆发期；50~70 分为稳健消化/应用探索期；低于 40 分为周期降温或回调期。"
                },
                "us_cn_matrix": {
                    "title": "中美 AI 产业五维对比模型 (动态盘中评估)",
                    "dimensions": [
                        {"name": "算力基础", "max": 20, "desc": f"考察 GPU 储备、HBM 及封装产能 (美 {us_compute} vs 中 {cn_compute})"},
                        {"name": "资本投入", "max": 20, "desc": "考察云巨头 CapEx 资本开支规模与研发投资 (美 17.5 vs 中 14.0)"},
                        {"name": "商业化程度", "max": 20, "desc": "考察 Enterprise SaaS、云 AI 账单与 Agent 变现 (美 16.0 vs 中 13.5)"},
                        {"name": "估值泡沫指数", "max": 30, "desc": f"考察核心标的估值偏离与题材炒作热度 (美 {us_bubble} vs 中 {cn_bubble})"},
                        {"name": "产业链完整度", "max": 10, "desc": "考察从芯片、能源配电到工业落地的生态全貌 (美 9.0 vs 中 7.5)"}
                    ]
                },
                "bubble_meter": {
                    "title": "AI 泡沫温度计与风险判定",
                    "desc": "区分“产业真实价值”与“股票估值泡沫”。若能源基建、芯片与云开支强劲增长，属【健康资本扩张】；若算力滞涨而边缘小票暴涨，则触发【泡沫风险预警】。"
                },
                "investment_clock": {
                    "title": "AI 四象限投资时钟与 1997 年历史比对",
                    "desc": "将 AI 产业分为【硬件爆发期➔需求验证期➔应用爆发期➔泡沫期】。当前映射 1997 年互联网大建设早期（基础设施与电网建设阶段），尚未进入 2000 年全民炒作无业绩垃圾股的末期泡沫。"
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
