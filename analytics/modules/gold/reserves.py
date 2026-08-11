"""
获取黄金资金面/基本面宏观数据：
1. 中国央行黄金与外汇储备 (macro_china_foreign_exchange_gold)
2. 全球最大黄金 ETF (SPDR Gold Trust) 持仓 (macro_cons_gold)
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any
from ...core.cache import cached
from ...core.config import settings
from ...core.utils import safe_float, get_beijing_time, akshare_call_with_retry
from ...core.logger import logger


class GoldFundFlows:
    """黄金资金面与储备分析"""

    @staticmethod
    @cached("metals:reserves:china_v4", ttl=86400, stale_ttl=172800)
    def get_china_gold_reserves() -> Dict[str, Any]:
        """获取中国央行黄金储备数据及分析"""
        try:
            df = akshare_call_with_retry(ak.macro_china_foreign_exchange_gold)
            if df.empty:
                raise ValueError("无法获取中国央行黄金储备数据")
            
            # 日期清洗与按时间排序 (纠正 string 字母排序的 Bug)
            def parse_date(date_str: str):
                parts = date_str.split('.')
                return int(parts[0]) * 100 + int(parts[1])
            
            df['sort_key'] = df['统计时间'].apply(parse_date)
            df = df.sort_values(by='sort_key').reset_index(drop=True)
            
            # 计算月度变动
            df['net_change'] = df['黄金储备'].diff()
            df['year'] = df['统计时间'].apply(lambda x: int(x.split('.')[0]))
            
            latest_row = df.iloc[-1]
            current_val = float(latest_row['黄金储备'])  # 万盎司
            net_change = float(latest_row['net_change']) if not pd.isna(latest_row['net_change']) else 0.0  # 万盎司
            
            # 吨换算: 10,000 ounces = 0.311035 tonnes
            current_tonnes = round(current_val * 0.311035, 1)
            net_change_tonnes = round(net_change * 0.311035, 2)
            
            # 计算 5 年分位数 (60 个月)
            recent_5y = df.tail(60)
            valid_changes = recent_5y['net_change'].dropna().tolist()
            if valid_changes:
                less_equal = sum(1 for x in valid_changes if x <= net_change)
                percentile = round((less_equal / len(valid_changes)) * 100, 1)
            else:
                percentile = 50.0
            
            # 统计值 (近 10 年)
            recent_10y = df.tail(120)
            hist_max = float(recent_10y['黄金储备'].max())
            hist_min = float(recent_10y['黄金储备'].min())
            hist_avg = float(recent_10y['黄金储备'].mean())
            
            # 构建说明文案
            explanation = (
                "中国央行黄金储备说明：\n"
                "• 数据来源：国家外汇管理局，按月公布期末存量数据\n"
                "• 换算比例：1万盎司 ≈ 0.311 吨\n"
                "• 净变动计算：当前月官方储备存量 - 上一月存量 = 当月净买入/卖出量\n"
                "• 核心逻辑：央行增持黄金是去美元化、资产多元化及避险的主动体现，长期持续的黄金增持为金价下限提供坚实的核心底部支撑。"
            )
            
            # 格式化日期显示 YYYY-MM
            date_parts = str(latest_row['统计时间']).split('.')
            formatted_date = f"{date_parts[0]}-{int(date_parts[1]):02d}"
            
            # 1. 月度历史 (最近 24 个月)
            monthly_history = []
            for idx, row in df.tail(24).iterrows():
                d_parts = str(row['统计时间']).split('.')
                d_formatted = f"{d_parts[0]}-{int(d_parts[1]):02d}"
                monthly_history.append({
                    "date": d_formatted,
                    "net_change_tonnes": round((float(row['net_change']) if not pd.isna(row['net_change']) else 0.0) * 0.311035, 2)
                })
                
            # 2. 年度历史 (最近 10 年)
            df_annual = df.groupby('year').agg({
                '黄金储备': 'last',
                'net_change': 'sum'
            }).reset_index()
            
            annual_history = []
            for idx, row in df_annual.tail(10).iterrows():
                annual_history.append({
                    "date": f"{int(row['year'])}年",
                    "net_change_tonnes": round((float(row['net_change']) if not pd.isna(row['net_change']) else 0.0) * 0.311035, 2)
                })
            
            return {
                "date": formatted_date,
                "current_value": round(current_val, 1),
                "current_tonnes": current_tonnes,
                "net_change": round(net_change, 1),
                "net_change_tonnes": net_change_tonnes,
                "percentile": percentile,
                "historical_high": round(hist_max, 1),
                "historical_low": round(hist_min, 1),
                "historical_avg": round(hist_avg, 1),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": explanation,
                "monthly_history": monthly_history,
                "annual_history": annual_history
            }
            
        except Exception as e:
            logger.error(f"❌ 获取中国央行黄金储备失败: {e}")
            return {"error": str(e), "current_value": 0.0}

    @staticmethod
    @cached("metals:reserves:spdr_v4", ttl=86400, stale_ttl=172800)
    def get_spdr_etf_holdings() -> Dict[str, Any]:
        """获取全球最大黄金 ETF (SPDR) 持仓数据及分析"""
        try:
            df = akshare_call_with_retry(ak.macro_cons_gold)
            if df.empty:
                raise ValueError("无法获取 SPDR 黄金持仓数据")
            
            df = df.sort_values(by='日期').reset_index(drop=True)
            
            df['total_inventory'] = pd.to_numeric(df['总库存'], errors='coerce')
            df['change'] = pd.to_numeric(df['增持/减持'], errors='coerce')
            df['total_value'] = pd.to_numeric(df['总价值'], errors='coerce')
            
            # 提取年、月用于重采样聚合
            def get_year_month(x):
                if hasattr(x, 'year'):
                    return x.year, x.month
                parts = str(x).split('-')
                return int(parts[0]), int(parts[1])

            df['year'] = df['日期'].apply(lambda x: get_year_month(x)[0])
            df['month'] = df['日期'].apply(lambda x: get_year_month(x)[1])
            
            latest_row = df.iloc[-1]
            current_tonnes = float(latest_row['total_inventory'])
            change_tonnes = float(latest_row['change']) if not pd.isna(latest_row['change']) else 0.0
            total_value_usd = float(latest_row['total_value'])
            
            # 计算 5 年分位数 (约 1250 个交易日)
            recent_5y = df.tail(1250)
            valid_inventories = recent_5y['total_inventory'].dropna().tolist()
            if valid_inventories:
                less_equal = sum(1 for x in valid_inventories if x <= current_tonnes)
                percentile = round((less_equal / len(valid_inventories)) * 100, 1)
            else:
                percentile = 50.0
                
            # 统计值 (近 5 年)
            hist_max = float(recent_5y['total_inventory'].max())
            hist_min = float(recent_5y['total_inventory'].min())
            hist_avg = float(recent_5y['total_inventory'].mean())
            
            explanation = (
                "SPDR Gold Trust 黄金持仓说明：\n"
                "• 数据来源：SPDR 官方持仓披露，按每个美股交易日晚间更新\n"
                "• 属性地位：全球规模及流动性最大的黄金实物 ETF，是全球金融机构 and 主力散户买卖黄金的最前沿指标\n"
                "• 核心逻辑：ETF 持仓变化代表微观民间和投资性资金配置实物金的意愿，与金价走势正相关极高，持仓高水位百分位代表看多情绪拥挤，反之代表抛售见底。"
            )
            
            # 1. 月度历史 (聚合，最近 24 个月)
            df_monthly = df.groupby(['year', 'month']).agg({
                'total_inventory': 'last',
                'change': 'sum'
            }).reset_index()
            
            monthly_history = []
            for idx, row in df_monthly.tail(24).iterrows():
                monthly_history.append({
                    "date": f"{int(row['year'])}-{int(row['month']):02d}",
                    "tonnes": float(row['total_inventory']),
                    "change": float(row['change']) if not pd.isna(row['change']) else 0.0
                })
                
            # 2. 年度历史 (聚合，最近 10 年)
            df_annual = df.groupby('year').agg({
                'total_inventory': 'last',
                'change': 'sum'
            }).reset_index()
            
            annual_history = []
            for idx, row in df_annual.tail(10).iterrows():
                annual_history.append({
                    "date": f"{int(row['year'])}年",
                    "tonnes": float(row['total_inventory']),
                    "change": float(row['change']) if not pd.isna(row['change']) else 0.0
                })
            
            return {
                "date": str(latest_row['日期']),
                "current_tonnes": round(current_tonnes, 2),
                "change_tonnes": round(change_tonnes, 2),
                "total_value_usd": total_value_usd,
                "percentile": percentile,
                "historical_high": round(hist_max, 2),
                "historical_low": round(hist_min, 2),
                "historical_avg": round(hist_avg, 2),
                "update_time": get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"),
                "explanation": explanation,
                "monthly_history": monthly_history,
                "annual_history": annual_history
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 SPDR 黄金持仓失败: {e}")
            return {"error": str(e), "current_tonnes": 0.0}
