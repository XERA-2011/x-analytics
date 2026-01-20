"""
中国国债收益率分析
获取国债收益率曲线和走势
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time


class CNBonds:
    """中国国债分析"""

    @staticmethod
    @cached("market_cn:bonds", ttl=settings.CACHE_TTL["bonds"], stale_ttl=600)
    def get_treasury_yields() -> Dict[str, Any]:
        """
        获取国债收益率数据

        Returns:
            国债收益率数据
        """
        try:
            print("📊 获取国债收益率数据...")
            # 获取国债收益率数据
            df = ak.bond_zh_us_rate()

            if df.empty:
                raise ValueError("国债收益率数据为空")

            print(f"✅ 获取到国债数据，共 {len(df)} 条记录")

            # 获取最新数据
            latest_data = df.iloc[-1]

            # 格式化收益率曲线
            yield_curve = {
                "1m": safe_float(latest_data.get("中国国债收益率1月", 0)),
                "3m": safe_float(latest_data.get("中国国债收益率3月", 0)),
                "6m": safe_float(latest_data.get("中国国债收益率6月", 0)),
                "1y": safe_float(latest_data.get("中国国债收益率1年", 0)),
                "2y": safe_float(latest_data.get("中国国债收益率2年", 0)),
                "3y": safe_float(latest_data.get("中国国债收益率3年", 0)),
                "5y": safe_float(latest_data.get("中国国债收益率5年", 0)),
                "7y": safe_float(latest_data.get("中国国债收益率7年", 0)),
                "10y": safe_float(latest_data.get("中国国债收益率10年", 0)),
                "30y": safe_float(latest_data.get("中国国债收益率30年", 0)),
            }

            # 计算收益率变化
            if len(df) > 1:
                prev_data = df.iloc[-2]
                yield_changes = {}
                for period in yield_curve.keys():
                    current = yield_curve[period]
                    previous = safe_float(
                        prev_data.get(
                            f"中国国债收益率{CNBonds._period_to_chinese(period)}",
                            current,
                        )
                    )
                    yield_changes[period] = round(current - previous, 4)
            else:
                yield_changes = {period: 0 for period in yield_curve.keys()}

            # 分析收益率曲线形态
            curve_analysis = CNBonds._analyze_yield_curve(yield_curve)

            # 获取历史走势（最近30天）
            history_data = CNBonds._get_yield_history(df)

            return {
                "yield_curve": yield_curve,
                "yield_changes": yield_changes,
                "curve_analysis": curve_analysis,
                "history": history_data,
                "key_rates": {
                    "10y": yield_curve["10y"],
                    "2y": yield_curve["2y"],
                    "spread_10y_2y": round(yield_curve["10y"] - yield_curve["2y"], 4),
                },
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            print(f"❌ 获取国债收益率失败: {e}")
            return {
                "error": str(e),
                "yield_curve": {},
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    @cached("market_cn:bond_analysis", ttl=settings.CACHE_TTL["bonds"], stale_ttl=600)
    def get_bond_market_analysis() -> Dict[str, Any]:
        """
        获取债券市场分析

        Returns:
            债券市场分析数据
        """
        try:
            # 获取国债收益率数据
            yield_data = CNBonds.get_treasury_yields()

            if "error" in yield_data:
                raise ValueError("无法获取收益率数据")

            # 分析市场状况
            analysis = {}

            # 1. 利率水平分析
            ten_year_yield = yield_data["key_rates"]["10y"]
            if ten_year_yield > 3.5:
                rate_level = "高位"
                rate_comment = "收益率处于相对高位，债券配置价值较高"
            elif ten_year_yield > 2.5:
                rate_level = "中位"
                rate_comment = "收益率处于中等水平"
            else:
                rate_level = "低位"
                rate_comment = "收益率处于相对低位，债券配置价值有限"

            analysis["rate_level"] = {
                "level": rate_level,
                "comment": rate_comment,
                "ten_year_yield": ten_year_yield,
            }

            # 2. 期限利差分析
            spread_10y_2y = yield_data["key_rates"]["spread_10y_2y"]
            if spread_10y_2y > 0.8:
                spread_status = "正常"
                spread_comment = "收益率曲线形态正常，长短端利差合理"
            elif spread_10y_2y > 0.2:
                spread_status = "平坦"
                spread_comment = "收益率曲线趋于平坦，需关注经济预期变化"
            else:
                spread_status = "倒挂"
                spread_comment = "收益率曲线倒挂，可能预示经济衰退风险"

            analysis["spread_analysis"] = {
                "status": spread_status,
                "comment": spread_comment,
                "spread_10y_2y": spread_10y_2y,
            }

            # 3. 投资建议
            investment_advice = CNBonds._get_investment_advice(
                ten_year_yield, spread_10y_2y
            )
            analysis["investment_advice"] = investment_advice

            analysis["update_time"] = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")

            return analysis

        except Exception as e:
            print(f"❌ 债券市场分析失败: {e}")
            return {
                "error": str(e),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def _period_to_chinese(period: str) -> str:
        """期限转换为中文"""
        mapping = {
            "1m": "1月",
            "3m": "3月",
            "6m": "6月",
            "1y": "1年",
            "2y": "2年",
            "3y": "3年",
            "5y": "5年",
            "7y": "7年",
            "10y": "10年",
            "30y": "30年",
        }
        return mapping.get(period, period)

    @staticmethod
    def _analyze_yield_curve(yield_curve: Dict[str, float]) -> Dict[str, Any]:
        """分析收益率曲线形态"""
        try:
            # 计算关键利差
            spread_10y_2y = yield_curve["10y"] - yield_curve["2y"]
            spread_10y_3m = yield_curve["10y"] - yield_curve["3m"]

            # 判断曲线形态
            if spread_10y_2y > 1.0:
                curve_shape = "陡峭"
                shape_comment = "收益率曲线较为陡峭，反映经济增长预期较强"
            elif spread_10y_2y > 0.2:
                curve_shape = "正常"
                shape_comment = "收益率曲线形态正常"
            elif spread_10y_2y > -0.2:
                curve_shape = "平坦"
                shape_comment = "收益率曲线趋于平坦，市场对未来经济增长预期谨慎"
            else:
                curve_shape = "倒挂"
                shape_comment = "收益率曲线出现倒挂，可能预示经济衰退风险"

            return {
                "shape": curve_shape,
                "comment": shape_comment,
                "spread_10y_2y": round(spread_10y_2y, 4),
                "spread_10y_3m": round(spread_10y_3m, 4),
            }

        except Exception as e:
            print(f"⚠️ 分析收益率曲线失败: {e}")
            return {"shape": "未知", "comment": "分析失败"}

    @staticmethod
    def _get_yield_history(df: pd.DataFrame, days: int = 30) -> List[Dict[str, Any]]:
        """获取收益率历史数据"""
        try:
            # 取最近30天的数据
            recent_df = df.tail(days)

            history = []
            for _, row in recent_df.iterrows():
                history.append(
                    {
                        "date": row.name.strftime("%Y-%m-%d")
                        if hasattr(row.name, "strftime")
                        else str(row.name),
                        "10y": safe_float(row.get("中国国债收益率10年", 0)),
                        "2y": safe_float(row.get("中国国债收益率2年", 0)),
                        "1y": safe_float(row.get("中国国债收益率1年", 0)),
                    }
                )

            return history

        except Exception as e:
            print(f"⚠️ 获取历史数据失败: {e}")
            return []

    @staticmethod
    def _get_investment_advice(ten_year_yield: float, spread: float) -> Dict[str, Any]:
        """获取投资建议"""
        advice = {
            "overall_rating": "中性",
            "duration_preference": "中等久期",
            "allocation_suggestion": "均衡配置",
            "risk_warning": "",
            "opportunities": [],
        }

        try:
            # 基于收益率水平的建议
            if ten_year_yield > 3.5:
                advice["overall_rating"] = "积极"
                advice["opportunities"].append("高收益率提供较好的配置价值")
                advice["allocation_suggestion"] = "可适当增加债券配置"
            elif ten_year_yield < 2.0:
                advice["overall_rating"] = "谨慎"
                advice["risk_warning"] = "收益率较低，配置价值有限"
                advice["allocation_suggestion"] = "建议降低债券配置比例"

            # 基于期限利差的建议
            if spread < 0:
                advice["duration_preference"] = "短久期"
                advice["risk_warning"] = "收益率曲线倒挂，经济衰退风险上升"
            elif spread > 1.5:
                advice["duration_preference"] = "长久期"
                advice["opportunities"].append("陡峭的收益率曲线有利于长久期债券")

            return advice

        except Exception as e:
            print(f"⚠️ 生成投资建议失败: {e}")
            return advice
