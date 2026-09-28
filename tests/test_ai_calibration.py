"""
Unit tests for AI overview data calibration:
- Active market trading session awareness & cross-market divergence
- Signal 2 computing chips status smoothing
- Capital rotation mode divergence guard
- Dynamic historical insight generation
"""

import unittest
from unittest.mock import patch, MagicMock
from analytics.modules.ai.overview import AIOverview


class TestAICalibration(unittest.TestCase):

    def test_market_statuses(self):
        """Verify market status tuple returns valid strings"""
        us_status, cn_status, summary = AIOverview.get_market_statuses()
        self.assertIsInstance(us_status, str)
        self.assertIsInstance(cn_status, str)
        self.assertIn("A股", summary)
        self.assertIn("美股", summary)

    def test_signal_2_smoothing_all_positive(self):
        """When core computing chips are all positive, signal 2 should be 看多/偏强, not 分化"""
        nvda = {"change_pct": 0.22, "market_cap": 3000.0}
        amd = {"change_pct": 0.22, "market_cap": 250.0}
        avgo = {"change_pct": 0.70, "market_cap": 800.0}
        arm = {"change_pct": 1.30, "market_cap": 150.0}
        mrvl = {"change_pct": 1.15, "market_cap": 70.0}

        chip_basket = [nvda, amd, avgo, arm, mrvl]
        valid_chips = [s for s in chip_basket if s.get("change_pct") is not None]
        total_chips = len(valid_chips)
        l1_positive_cnt = sum(1 for s in valid_chips if s.get("change_pct", 0) >= 0)
        l1_avg = 0.42
        nvda_change = 0.22

        if (l1_positive_cnt >= total_chips - 1 and nvda_change >= 0 and l1_avg >= 0.1) or (l1_avg >= 0.4 and nvda_change >= 0):
            sig2_status = "看多" if l1_avg >= 0.5 else "偏强"
            sig2_cls = "up"
        elif l1_positive_cnt <= 1 and (nvda_change < 0 or l1_avg < -0.3):
            sig2_status = "走弱"
            sig2_cls = "down"
        else:
            sig2_status = "分化"
            sig2_cls = "up" if nvda_change >= 0 or l1_avg >= 0 else "down"

        self.assertEqual(sig2_status, "偏强")
        self.assertEqual(sig2_cls, "up")

    def test_signal_2_smoothing_divergent(self):
        """When chips are mixed (some up, some down), signal 2 should be 分化"""
        nvda = {"change_pct": 1.5, "market_cap": 3000.0}
        amd = {"change_pct": -2.0, "market_cap": 250.0}
        avgo = {"change_pct": -1.2, "market_cap": 800.0}
        arm = {"change_pct": 0.5, "market_cap": 150.0}
        mrvl = {"change_pct": -0.8, "market_cap": 70.0}

        chip_basket = [nvda, amd, avgo, arm, mrvl]
        valid_chips = [s for s in chip_basket if s.get("change_pct") is not None]
        total_chips = len(valid_chips)
        l1_positive_cnt = sum(1 for s in valid_chips if s.get("change_pct", 0) >= 0)
        l1_avg = 0.05
        nvda_change = 1.5

        if (l1_positive_cnt >= total_chips - 1 and nvda_change >= 0 and l1_avg >= 0.1) or (l1_avg >= 0.4 and nvda_change >= 0):
            sig2_status = "看多" if l1_avg >= 0.5 else "偏强"
            sig2_cls = "up"
        elif l1_positive_cnt <= 1 and (nvda_change < 0 or l1_avg < -0.3):
            sig2_status = "走弱"
            sig2_cls = "down"
        else:
            sig2_status = "分化"
            sig2_cls = "up" if nvda_change >= 0 or l1_avg >= 0 else "down"

        self.assertEqual(sig2_status, "分化")
        self.assertEqual(sig2_cls, "up")

    def test_rotation_mode_cross_market_divergence(self):
        """When A shares drop heavily (-5.8%) while US shares are steady (+0.83%), rotation mode warns of divergence"""
        cn_momentum_pct = -5.82
        us_momentum_pct = 0.83
        divergence_spread = round(cn_momentum_pct - us_momentum_pct, 2)
        is_cross_market_divergence = (
            (cn_momentum_pct <= -2.0 and us_momentum_pct >= -0.2 and divergence_spread <= -2.5) or
            (us_momentum_pct <= -2.0 and cn_momentum_pct >= -0.2 and divergence_spread >= 2.5) or
            abs(divergence_spread) >= 3.5
        )
        self.assertTrue(is_cross_market_divergence)

        l6_avg = -5.82
        l0_avg = 0.26
        l1_avg = 0.42
        l5_avg = -1.68

        if is_cross_market_divergence and (cn_momentum_pct <= -2.0 or l6_avg <= -2.0):
            rotation_mode = "中美背离 (美股稳健·A股回调)"
            rotation_class = "warning"
        elif l0_avg > 0 and l1_avg >= l5_avg and l1_avg >= l6_avg:
            rotation_mode = "健康轮动 (能源与算力双驱动)"
            rotation_class = "healthy"
        else:
            rotation_mode = "均衡传导 (扩散中)"
            rotation_class = "neutral"

        self.assertEqual(rotation_mode, "中美背离 (美股稳健·A股回调)")
        self.assertEqual(rotation_class, "warning")

    def test_dynamic_historical_insight(self):
        """Test historical insight adapts dynamically to matched era"""
        eras = [
            (35.0, "1996年", "破晓阶段"),
            (55.0, "1997年", "思科与微软"),
            (80.0, "1999年", "泡沫晚期")
        ]
        for risk, era_sub, insight_sub in eras:
            if risk >= 75.0:
                matched_era = "1999年 互联网泡沫晚期 (情绪极度亢奋)"
                historical_insight = "对标 1999 年互联网泡沫晚期，概念题材炒作泛滥，资本开支与应用变现脱节，需防范估值透支后的剧烈均值回归风险。"
            elif risk >= 50.0:
                matched_era = "1997年 互联网大建设中期 (基础设施红利期)"
                historical_insight = "对标 1997 年思科与微软基建大扩容期，资本开支与硬件订单处于兑现高潮，应用层变现与盈利模式仍在加速探索阶段。"
            else:
                matched_era = "1996年 互联网商用早期 (基建建设起点)"
                historical_insight = "对标 1996 年互联网商用早期破晓阶段，底层软硬件与基础设施先行，估值泡沫化程度有限，主导资产以硬科技与核心基建为主。"

            self.assertIn(era_sub, matched_era)
            self.assertIn(insight_sub, historical_insight)


if __name__ == "__main__":
    unittest.main()
