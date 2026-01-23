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
from ...core.logger import logger


class CNBonds:
    """中国国债分析"""

    @staticmethod
    @cached("market_cn:bonds", ttl=settings.CACHE_TTL["bonds"], stale_ttl=settings.CACHE_TTL["bonds"] * settings.STALE_TTL_RATIO)
    def get_treasury_yields() -> Dict[str, Any]:
        """
        获取国债收益率数据 (混合数据源)
        """
        try:
            logger.info("📊 获取国债收益率数据(主源)...")
            
            # 1. 主数据源: 中债国债收益率曲线 (覆盖大部分期限)
            # 动态计算日期范围 (取最近3个月)
            end_date = get_beijing_time()
            start_date = end_date - pd.Timedelta(days=90)
            
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            df_primary = pd.DataFrame()
            try:
                df_primary = ak.bond_china_yield(start_date=start_str, end_date=end_str)
                # 过滤只保留国债
                if not df_primary.empty and "曲线名称" in df_primary.columns:
                    df_primary = df_primary[df_primary["曲线名称"] == "中债国债收益率曲线"]
                    # 排序
                    if "日期" in df_primary.columns:
                        df_primary["日期"] = pd.to_datetime(df_primary["日期"])
                        df_primary = df_primary.sort_values("日期")
            except Exception as e:
                logger.warning(f" 主数据源获取失败: {e}")

            # 2. 补充数据源: Investing (用于补充 2年期 等缺失数据)
            logger.info("📊 获取国债收益率数据(补充源)...")
            df_sec = pd.DataFrame()
            try:
                # 该接口虽然经常被封, 但包含关键的 2Y 数据
                # 这里不抛出异常，失败了就只用主源
                from ...core.utils import akshare_call_with_retry
                df_sec = akshare_call_with_retry(ak.bond_zh_us_rate, max_retries=2)
            except Exception as e:
                logger.warning(f" 补充数据源获取失败: {e}")

            if df_primary.empty and df_sec.empty:
                raise ValueError("所有国债数据源均不可用")

            # 准备数据提取
            # 主源最新数据
            latest_pri = df_primary.iloc[-1] if not df_primary.empty else {}
            prev_pri = df_primary.iloc[-2] if len(df_primary) > 1 else latest_pri
            
            # 补充源最新数据
            latest_sec = df_sec.iloc[-1] if not df_sec.empty else {}
            prev_sec = df_sec.iloc[-2] if len(df_sec) > 1 else latest_sec

            # 映射表: key -> (主源列名, 补充源列名)
            curve_mapping = {
                "1m": ("1月", None),        # 1M 主源无，补充源无?
                "3m": ("3月", None),
                "6m": ("6月", None),
                "1y": ("1年", None),
                "2y": ("2年", "中国国债收益率2年"),  # 关键: 2Y 主源缺，补充源有
                "3y": ("3年", "中国国债收益率3年"), # 注意补充源可能也没3y, 视column而定
                "5y": ("5年", "中国国债收益率5年"),
                "7y": ("7年", None),
                "10y": ("10年", "中国国债收益率10年"),
                "30y": ("30年", "中国国债收益率30年")
            }

            yield_curve = {}
            yield_changes = {}

            for key, (col_pri, col_sec) in curve_mapping.items():
                current_val = None
                prev_val = None
                
                # 优先尝试主源
                if col_pri and not df_primary.empty:
                    val = latest_pri.get(col_pri)
                    if pd.notna(val):
                        current_val = safe_float(val, default=None)
                        # 前值
                        p_val = prev_pri.get(col_pri)
                        prev_val = safe_float(p_val, default=None)

                # 如果主源没有(或无效)，尝试补充源
                if current_val is None and col_sec and not df_sec.empty:
                    val = latest_sec.get(col_sec)
                    if pd.notna(val):
                        current_val = safe_float(val, default=None)
                        # 前值
                        p_val = prev_sec.get(col_sec)
                        prev_val = safe_float(p_val, default=None)
                
                # 依然没有? 那就是真没有了 (如 1m)
                yield_curve[key] = current_val
                
                # 计算涨跌 (如果都有值)
                if current_val is not None and prev_val is not None:
                    yield_changes[key] = round((current_val - prev_val) * 100, 2) # BP
                else:
                    yield_changes[key] = 0 # 或 None, 前端处理 0 也可以(无变化)

            logger.info(" 国债数据整合完成")

            # 分析收益率曲线形态
            curve_analysis = CNBonds._analyze_yield_curve(yield_curve)

            # 获取历史走势（最近30天）
            history_data = CNBonds._get_yield_history(df_primary)

            # 安全计算利差（处理 None 值）
            ten_y = yield_curve.get("10y")
            two_y = yield_curve.get("2y")
            spread_10y_2y = (
                round(ten_y - two_y, 4)
                if ten_y is not None and two_y is not None
                else None
            )

            return {
                "yield_curve": yield_curve,
                "yield_changes": yield_changes,
                "curve_analysis": curve_analysis,
                "history": history_data,
                "key_rates": {
                    "10y": ten_y,
                    "2y": two_y,
                    "spread_10y_2y": spread_10y_2y,
                },
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            logger.error(f" 获取国债收益率失败: {e}")
            return {
                "error": str(e),
                "yield_curve": {},
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    @cached("market_cn:bond_analysis", ttl=settings.CACHE_TTL["bonds"], stale_ttl=settings.CACHE_TTL["bonds"] * settings.STALE_TTL_RATIO)
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

            # 分析市场状况 (基于基础数据扩展)
            analysis = yield_data.copy()

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

            analysis["update_time"] = get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")

            return analysis

        except Exception as e:
            logger.error(f" 债券市场分析失败: {e}")
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
    def _analyze_yield_curve(yield_curve: Dict[str, Any]) -> Dict[str, Any]:
        """分析收益率曲线形态"""
        try:
            # 安全获取收益率值
            ten_y = yield_curve.get("10y")
            two_y = yield_curve.get("2y")
            three_m = yield_curve.get("3m")

            # 检查必要数据是否存在
            if ten_y is None or two_y is None:
                return {
                    "shape": "未知",
                    "comment": "关键数据缺失，无法分析曲线形态",
                    "spread_10y_2y": None,
                    "spread_10y_3m": None,
                }

            # 计算关键利差
            spread_10y_2y = ten_y - two_y
            spread_10y_3m = ten_y - three_m if three_m is not None else None

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
                "spread_10y_3m": round(spread_10y_3m, 4) if spread_10y_3m is not None else None,
            }

        except Exception as e:
            logger.warning(f" 分析收益率曲线失败: {e}")
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
            logger.warning(f" 获取历史数据失败: {e}")
            return []
