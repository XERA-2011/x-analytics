from tortoise import fields, models

class SentimentHistory(models.Model):
    """
    Historical record of market sentiment (Fear & Greed Index).
    """
    id = fields.IntField(pk=True)
    date = fields.DateField(index=True)
    market = fields.CharField(max_length=10, index=True, default="CN")  # CN, US, HK, Metals, Gold, Silver
    indicator_type = fields.CharField(max_length=50, default="fear_greed", index=True)
    score = fields.FloatField()
    level = fields.CharField(max_length=20)
    
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "sentiment_history"
        unique_together = ("date", "market", "indicator_type")

    def __str__(self):
        return f"{self.date} [{self.market}]: {self.score} ({self.level})"
