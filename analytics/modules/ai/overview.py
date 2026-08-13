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
        "ai:overview_v7", 
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

            # 检查 A股 板块行情是否为空或处于非交易时间（所有板块涨跌幅为 0 且无有效领涨股）
            is_empty_market = True
            if cn_ai_sectors:
                for s in cn_ai_sectors:
                    if s.get("change_pct", 0.0) != 0.0 or (s.get("top_stock") and s["top_stock"] not in ("", "--")):
                        is_empty_market = False
                        break
            else:
                is_empty_market = True

            # 若板块无有效数据，强制使用 A股 核心龙头个股（有收盘价/实时价格）支撑 L6，避免展示空白占位符
            if is_empty_market and cn_ai_leaders:
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

            l6_visible_sectors = cn_ai_sectors[:4]
            l6_avg = sum(s["change_pct"] for s in l6_visible_sectors) / len(l6_visible_sectors) if l6_visible_sectors else 0.0

            # 3.5 行业层级均值平滑处理 (使用 Redis 存储滚动均值，过滤盘中高频噪音)
            import json
            from ...core.cache import cache
            if cache.connected and cache.redis:
                try:
                    history_key = f"{settings.CACHE_PREFIX}:ai:layers_avg_history"
                    current_averages = {
                        "l0": l0_avg, "l1": l1_avg, "l2": l2_avg,
                        "l3": l3_avg, "l4": l4_avg, "l5": l5_avg, "l6": l6_avg
                    }
                    # 放入 Redis 列表
                    cache.redis.lpush(history_key, json.dumps(current_averages))
                    cache.redis.ltrim(history_key, 0, 4)  # 保留最近 5 次记录

                    # 获取历史并计算滑动平均
                    history_items = cache.redis.lrange(history_key, 0, -1)
                    history_dicts = []
                    for item in history_items:
                        if item:
                            try:
                                history_dicts.append(json.loads(item))
                            except Exception:
                                pass
                    if history_dicts:
                        l0_avg = sum(d["l0"] for d in history_dicts) / len(history_dicts)
                        l1_avg = sum(d["l1"] for d in history_dicts) / len(history_dicts)
                        l2_avg = sum(d["l2"] for d in history_dicts) / len(history_dicts)
                        l3_avg = sum(d["l3"] for d in history_dicts) / len(history_dicts)
                        l4_avg = sum(d["l4"] for d in history_dicts) / len(history_dicts)
                        l5_avg = sum(d["l5"] for d in history_dicts) / len(history_dicts)
                        l6_avg = sum(d["l6"] for d in history_dicts) / len(history_dicts)
                        logger.info(f"✅ [Redis] AI layer averages smoothed over {len(history_dicts)} records.")
                except Exception as smooth_err:
                    logger.warning(f"⚠️ Redis平滑均值处理失败，使用当前未平滑数据: {smooth_err}")

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
                    "items": l6_visible_sectors,
                    "desc": "A股半导体与 AI 游资概念题材，若边缘小票狂热暴涨往往预示短线情绪近尾声。"
                }
            ]

            # 4. AI 市场热度分 (短线行情指标)
            # 当前七因子主要由各层标的涨跌幅组成，反映市场热度，不等同于产业基本面周期。
            weighted_pct = (
                l0_avg * 0.10 + 
                l1_avg * 0.25 + 
                l2_avg * 0.20 + 
                l3_avg * 0.15 + 
                l4_avg * 0.10 + 
                l5_avg * 0.10 + 
                l6_avg * 0.10
            )
            heat_score = min(100.0, max(0.0, 50.0 + weighted_pct * 7.5))
            heat_score = round(heat_score, 1)

            # 5. AI 资金轮动健康度判定 (先判定轮动格局，确保与周期风险全局自洽)
            if l0_avg > 0 and l1_avg >= l5_avg and l1_avg >= l6_avg:
                rotation_mode = "健康轮动 (能源与算力双驱动)"
                rotation_class = "healthy"
                rotation_desc = "资金优先集中于电力基础设施 (L0)、芯片 (L1) 与存储 (L2)，电力开支 + 芯片强劲 = 健康 AI 扩张期。"
            elif l6_avg > l1_avg and l6_avg > 1.5:
                rotation_mode = "泡沫轮动 (概念投机)"
                rotation_class = "bubble"
                rotation_desc = "边缘小票与概念题材快速轮动暴涨，算力与电力主线动能相对偏弱，警惕短线情绪过热。"
            else:
                rotation_mode = "均衡传导 (扩散中)"
                rotation_class = "neutral"
                rotation_desc = "资金由算力芯片与电力基建向数据中心及企业级 Agent 应用平稳传导。"

            # 6. 周期阶段与综合风险判定 (融合资金轮动与泡沫对冲，消除结论冲突)
            if rotation_class == "bubble":
                if nvda["change_pct"] > 0:
                    cycle_phase = "结构性过热与概念扩散期"
                    cycle_status = "warning"
                    cycle_desc = "核心算力高位震荡。机会聚焦：★★☆☆☆ 概念题材投机 | 风险警示：估值安全性承压，警惕短线情绪退潮。"
                    trend_str = "⚠️ 结构分化"
                    risk_level = "中等"
                    risk_class = "medium"
                else:
                    cycle_phase = "估值过热 / 泡沫预警期"
                    cycle_status = "warning"
                    cycle_desc = "算力龙头滞涨。机会聚焦：★☆☆☆☆ 观望或轻仓防御 | 风险警示：题材疯狂炒作，警惕高位见顶回调。"
                    trend_str = "⚠️ 泡沫预警"
                    risk_level = "偏高"
                    risk_class = "high"
            elif nvda["change_pct"] < -2.0 and l4_avg < -1.5:
                cycle_phase = "周期回调降温期"
                cycle_status = "cooling"
                cycle_desc = "云巨头 CapEx 情绪回落。机会聚焦：★★★☆☆ 算力与基建回调左侧布局 | 风险警示：大厂开支环比放缓，防守为主。"
                trend_str = "↓ 回调"
                risk_level = "偏高"
                risk_class = "high"
            elif rotation_class == "healthy" and nvda["change_pct"] > 0.3 and l0_avg > 0.2:
                cycle_phase = "能源与算力共振爆发期"
                cycle_status = "active"
                cycle_desc = "AI 电网基建与算力强共振。机会聚焦：★★★★★ 算力芯片、存储封装与电力设备 | 风险警示：警惕核心标的高估值震荡。"
                trend_str = "↑ 强劲"
                risk_level = "低"
                risk_class = "low"
            else:
                cycle_phase = "稳健消化与应用探索期"
                cycle_status = "neutral"
                if l5_avg >= 2.0:
                    cycle_desc = "基建向应用传导。机会聚焦：★★★★☆ 液冷基建、HBM 存储与 Agent 商业化落地 | 风险警示：警惕应用端估值随情绪过快推高。"
                else:
                    cycle_desc = "基建向应用传导。机会聚焦：★★★★☆ 液冷基建与 HBM 存储 | 风险警示：关注软件变现与应用账单实际兑现度。"
                trend_str = "→ 震荡"
                risk_level = "中等"
                risk_class = "medium"

            # 7. 中美 AI 五维对比模型 (统一为正向指标：面积越大优势越大，解决泡沫反向误导问题)
            cn_core_avg = sum(s["change_pct"] for s in cn_ai_leaders) / len(cn_ai_leaders) if cn_ai_leaders else l6_avg
            
            # 动态微调
            us_compute = round(min(20.0, max(10.0, 18.5 + l1_avg * 0.2)), 1)
            cn_compute = round(min(20.0, max(8.0, 12.0 + cn_core_avg * 0.3)), 1)
            
            us_bubble_raw = round(min(30.0, max(10.0, 18.0 + (l1_avg - l5_avg) * 0.5)), 1)
            cn_bubble_raw = round(min(30.0, max(12.0, 23.5 + (l6_avg - cn_core_avg) * 0.8)), 1)

            # 转换为“估值安全性”正向指标 (30 - 泡沫指数 = 安全边际得分，分值越高越安全/泡沫越小)
            us_safety = round(max(5.0, min(30.0, 30.0 - (us_bubble_raw - 10.0) * 0.8)), 1)
            cn_safety = round(max(5.0, min(30.0, 30.0 - (cn_bubble_raw - 10.0) * 0.8)), 1)

            us_cn_comparison = {
                "compute_base": {"us": us_compute, "cn": cn_compute, "max": 20, "label": "算力基础"},
                "capex_investment": {"us": 17.5, "cn": 14.0, "max": 20, "label": "资本投入"},
                "commercialization": {"us": 16.0, "cn": 13.5, "max": 20, "label": "商业化程度"},
                "valuation_safety": {"us": us_safety, "cn": cn_safety, "max": 30, "label": "估值安全性", "raw_bubble_us": us_bubble_raw, "raw_bubble_cn": cn_bubble_raw},
                "completeness": {"us": 9.0, "cn": 7.5, "max": 10, "label": "产业链完整度"}
            }

            # 8. AI 泡沫温度计 (Bubble Thermometer)
            bubble_meter = {
                "us": {
                    "value_score": round(min(100, max(50, 82 + l0_avg + l1_avg)), 1),
                    "bubble_risk": round(us_bubble_raw * 3.2, 1),
                    "status_text": "健康资本扩张",
                    "status_class": "healthy"
                },
                "cn": {
                    "value_score": round(min(100, max(40, 64 + cn_core_avg)), 1),
                    "bubble_risk": round(cn_bubble_raw * 3.1, 1),
                    "status_text": "主题情绪扩散",
                    "status_class": "warning"
                }
            }

            # 9. AI 历史周期比较 (基于中美平均泡沫风险动态适配映射模型)
            avg_bubble_risk = (us_bubble_raw * 3.2 + cn_bubble_raw * 3.1) / 2
            if avg_bubble_risk >= 70.0:
                matched_era = "1999年 互联网泡沫晚期 (情绪极度亢奋)"
                similarity_pct = round(85.0 + (avg_bubble_risk - 70.0) * 0.3, 1)
                bubble_distance = "距离泡沫破裂阶段约 1 个周期阶段"
                summary_desc = "当前中美 AI 估值偏离度极高，资金向边缘股疯狂倾斜，已呈现 1999 年末期泡沫特征，需高度警惕阶段性泡沫破裂风险。"
            elif avg_bubble_risk >= 50.0:
                matched_era = "1997年 互联网大建设中期 (基础设施红利期)"
                similarity_pct = 85.0
                bubble_distance = "距离泡沫破裂阶段约 2 个周期阶段"
                summary_desc = "当前 AI 处于基础设施大建设与电力算力红利期，类似 1997 年卖服务器/路由器阶段，尚未进入 2000 年全民炒作无业绩垃圾股的末期泡沫。"
            else:
                matched_era = "1996年 互联网商用早期 (基建建设起点)"
                similarity_pct = round(80.0 + (50.0 - avg_bubble_risk) * 0.4, 1)
                bubble_distance = "距离泡沫破裂阶段约 3 个周期阶段"
                summary_desc = "当前全球 AI 产业链资本支出温和，硬件与算力处于稳健扩张或降温期，相似于 1996 年互联网起步阶段，安全边际高。"

            historical_match = {
                "matched_era": matched_era,
                "similarity_pct": similarity_pct,
                "bubble_distance": bubble_distance,
                "summary": summary_desc
            }

            # 10. AI 四象限投资时钟
            investment_clock = {
                "quadrant": "硬件与能源爆发期",
                "us_position": {"x": 72, "y": 85, "stage": "能源与硬件扩张 ➔ 应用验证"},
                "cn_position": {"x": 50, "y": 64, "stage": "基建建设 ➔ 应用探索"}
            }

            # 11. 四大核心验证信号 (多标的综合研判，消除单一标的偏颇与选择性摘录)
            # 信号1: 能源电力
            sig1_status = "充足" if l0_avg >= 0.5 else ("平稳" if l0_avg >= 0 else "紧张")
            sig1_cls = "up" if l0_avg >= 0 else "down"
            sig1_desc = f"GEV ({gev['change_pct']:+.2f}%) / CEG ({ceg['change_pct']:+.2f}%) / VST ({vst['change_pct']:+.2f}%)"

            # 信号2: 算力龙头动向 (综合 NVDA + 全组芯片均值)
            l1_positive_cnt = sum(1 for s in [nvda, amd, avgo, arm, mrvl] if s["change_pct"] >= 0)
            if l1_avg >= 0.5 and nvda["change_pct"] >= 0:
                sig2_status = "看多"
                sig2_cls = "up"
            elif nvda["change_pct"] >= 0 or l1_positive_cnt >= 3:
                sig2_status = "分化"
                sig2_cls = "up"
            else:
                sig2_status = "走弱"
                sig2_cls = "down"
            sig2_desc = f"英伟达 ({nvda['change_pct']:+.2f}%) · 博通 ({avgo['change_pct']:+.2f}%) · ARM ({arm['change_pct']:+.2f}%)"

            # 信号3: 存储/代工/光刻验证 (综合美光 MU + 台积电 TSM + 阿斯麦 ASML)
            if l2_avg >= 0.8:
                sig3_status = "强劲"
                sig3_cls = "up"
            elif l2_avg >= 0:
                sig3_status = "稳健"
                sig3_cls = "up"
            else:
                sig3_status = "承压"
                sig3_cls = "down"
            sig3_desc = f"美光 ({mu['change_pct']:+.2f}%) · 台积电 ({tsm['change_pct']:+.2f}%) · 阿斯麦 ({asml['change_pct']:+.2f}%)"

            # 信号4: 云巨头 CapEx 支撑
            sig4_status = "扩张" if l4_avg >= 0.5 else ("稳定" if l4_avg >= -0.5 else "放缓")
            sig4_cls = "up" if l4_avg >= -0.5 else "down"
            sig4_desc = f"微软/谷歌/亚马逊/Meta/甲骨文 5大巨头均值 ({l4_avg:+.2f}%)"

            signals = [
                {"title": "信号1：能源电力保障", "status": sig1_status, "status_class": sig1_cls, "desc": sig1_desc},
                {"title": "信号2：算力芯片动向", "status": sig2_status, "status_class": sig2_cls, "desc": sig2_desc},
                {"title": "信号3：存储代工验证", "status": sig3_status, "status_class": sig3_cls, "desc": sig3_desc},
                {"title": "信号4：云巨头 CapEx 支撑", "status": sig4_status, "status_class": sig4_cls, "desc": sig4_desc}
            ]

            # 12. 指标与公式透明化说明
            explanations = {
                "cycle_score": {
                    "title": "AI 市场热度分（短线行情动能）七因子模型",
                    "formula": "得分范围 0~100 分。加权涨跌幅 weighted_pct = L0*10% + L1*25% + L2*20% + L3*15% + L4*10% + L5*10% + L6*10%。基准分 = Min(100, Max(0, 50.0 + weighted_pct * 7.5))。",
                    "weights": [
                        {"layer": "L0 能源电力", "weight": "10%", "targets": "GEV (电气), CEG (核电), VST, ETN"},
                        {"layer": "L1 算力芯片", "weight": "25%", "targets": "NVDA, AMD, AVGO, ARM, MRVL, SMH"},
                        {"layer": "L2 存储代工", "weight": "20%", "targets": "MU (HBM), TSM (CoWoS), ASML"},
                        {"layer": "L3 数据中心", "weight": "15%", "targets": "SMCI (服务器), VRT (液冷), DELL"},
                        {"layer": "L4 云巨头CapEx", "weight": "10%", "targets": "MSFT, GOOGL, AMZN, META, ORCL"},
                        {"layer": "L5 Agent与应用", "weight": "10%", "targets": "PLTR, NOW, CRM"},
                        {"layer": "L6 A股概念题材", "weight": "10%", "targets": "A股半导体、通信设备及 AI 龙头"}
                    ],
                    "interpretation": "得分 70+ 分表示当前代表标的行情动能较强；50~70 分表示中性；低于 40 分表示短线动能偏弱。该指标不直接代表产业基本面周期。"
                },
                "us_cn_matrix": {
                    "title": "中美 AI 产业五维对比模型 (正向综合竞争力雷达图)",
                    "dimensions": [
                        {"name": "算力基础", "max": 20, "desc": f"考察 GPU 储备、HBM 及封装产能 (美 {us_compute} vs 中 {cn_compute})"},
                        {"name": "资本投入", "max": 20, "desc": "考察云巨头 CapEx 资本开支规模与研发投资 (美 17.5 vs 中 14.0)"},
                        {"name": "商业化程度", "max": 20, "desc": "考察 Enterprise SaaS、云 AI 账单与 Agent 变现 (美 16.0 vs 中 13.5)"},
                        {"name": "估值安全性", "max": 30, "desc": f"考察估值合理性与安全边际 (反向泡沫指数：分值越高代表泡沫越小、安全边际越高；美 {us_safety} vs 中 {cn_safety})"},
                        {"name": "产业链完整度", "max": 10, "desc": "考察从芯片、能源配电到工业落地的生态全貌 (美 9.0 vs 中 7.5)"}
                    ]
                },
                "bubble_meter": {
                    "title": "AI 泡沫温度计与风险判定",
                    "desc": "区分“产业真实价值”与“股票估值泡沫”。若能源基建、芯片与云开支强劲增长，属【健康资本扩张】；若算力滞涨而边缘小票暴涨，则触发【泡沫风险预警】。"
                },
                "rotation": {
                    "title": "AI 资金轮动监测与传导判定模型",
                    "desc": "基于 L0(能源电力)、L1(算力芯片)、L5(应用) 和 L6(边缘题材) 的盘中实时动能对比动态推演。【健康轮动】：资金优先集中于电力基建与核心芯片；【泡沫轮动】：边缘小票狂热暴涨而硬件停滞；【均衡传导】：资金由基建平稳向数据中心及 Agent 应用传导。"
                },
                "investment_clock": {
                    "title": "AI 四象限投资时钟与 1997 年历史比对",
                    "desc": "将 AI 产业分为【硬件爆发期➔需求验证期➔应用爆发期➔泡沫期】。当前映射 1997 年互联网大建设早期（基础设施与电网建设阶段），尚未进入 2000 年全民炒作无业绩垃圾股的末期泡沫。"
                }
            }

            # 13. 扩散 Roadmap 动态阶段数据 (动态提取单一主导阶段与活跃阶段，消除双主导并列歧义)
            active_stage_list = [1, 2] if rotation_class == "healthy" else ([5] if rotation_class == "bubble" else [3, 4])
            stages_data = [
                {"id": 1, "name": "阶段 1: 能源与算力芯片", "symbols": "GEV / NVDA / ARM", "avg_change": round(l0_avg * 0.4 + l1_avg * 0.6, 2), "status": "火热" if l1_avg >= 0 else "走弱"},
                {"id": 2, "name": "阶段 2: 存储与先进封装", "symbols": "美光 MU / 台积电 TSM", "avg_change": round(l2_avg, 2), "status": "火热" if l2_avg >= 0 else "走弱"},
                {"id": 3, "name": "阶段 3: 基建与液冷电源", "symbols": "SMCI / VRT / DELL", "avg_change": round(l3_avg, 2), "status": "稳健" if l3_avg >= 0 else "承压"},
                {"id": 4, "name": "阶段 4: 云巨头 & Agent", "symbols": "MSFT / PLTR / SaaS", "avg_change": round(l4_avg * 0.5 + l5_avg * 0.5, 2), "status": "稳健" if l4_avg >= 0 else "承压"},
                {"id": 5, "name": "阶段 5: 概念炒作 (泡沫)", "symbols": "边缘概念题材", "avg_change": round(l6_avg, 2), "status": "过热" if l6_avg > 2.0 else "平淡"},
            ]

            leading_stage = None
            max_change = -999.0
            for stage_id in active_stage_list:
                s_item = next((s for s in stages_data if s["id"] == stage_id), None)
                if s_item and s_item["avg_change"] > max_change:
                    max_change = s_item["avg_change"]
                    leading_stage = stage_id

            diffusion_roadmap = {
                "active_stages": active_stage_list,
                "leading_stage": leading_stage,
                "stages": stages_data
            }

            return {
                "cycle_score": heat_score,
                "heat_score": heat_score,
                "market_heat_score": heat_score,
                "industry_cycle_score": None,
                "score_scope": "market_heat",
                "score_note": "当前评分基于产业链代表标的行情动能，反映短线市场热度；产业基本面周期评分待接入 CapEx、订单、产能与收入等中长期数据。",
                "cycle_phase": cycle_phase,
                "cycle_status": cycle_status,
                "cycle_desc": cycle_desc,
                "trend_str": trend_str,
                "risk_level": risk_level,
                "risk_class": risk_class,
                "layers": layers,
                "us_cn_comparison": us_cn_comparison,
                "bubble_meter": bubble_meter,
                "rotation_mode": rotation_mode,
                "rotation_class": rotation_class,
                "rotation_desc": rotation_desc,
                "historical_match": historical_match,
                "investment_clock": investment_clock,
                "signals": signals,
                "diffusion_roadmap": diffusion_roadmap,
                "explanations": explanations,
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 AI 产业周期数据失败: {e}", exc_info=True)
            return {"error": f"获取 AI 产业周期数据失败: {str(e)}"}
