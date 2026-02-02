"""
超买超卖信号历史记录模型
"""

from tortoise import fields, models


class SignalHistory(models.Model):
    """
    超买超卖信号历史记录
    用于存储历史信号数据，支持分位数计算
    """
    id = fields.IntField(pk=True)
    date = fields.DateField(index=True)
    symbol = fields.CharField(max_length=20, index=True)  # sh000001, .INX, au0
    market = fields.CharField(max_length=10, index=True)  # CN, US, GOLD, SILVER
    period = fields.CharField(max_length=10, default="daily")  # daily, 60min

    # 综合信号
    signal = fields.CharField(max_length=15)  # overbought, oversold, neutral
    strength = fields.FloatField()

    # 各指标快照
    rsi = fields.FloatField(null=True)
    macd_histogram = fields.FloatField(null=True)
    bollinger_position = fields.FloatField(null=True)  # -1.5 to 1.5
    kdj_k = fields.FloatField(null=True)
    kdj_d = fields.FloatField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "signal_history"
        unique_together = ("date", "symbol", "period")

    def __str__(self):
        return f"{self.date} [{self.symbol}]: {self.signal} ({self.strength})"
