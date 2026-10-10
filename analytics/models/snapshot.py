from tortoise import fields
from tortoise.models import Model


class DataSnapshot(Model):
    """
    通用数据快照持久化模型
    用于缓存失效/冷启动时提供 0ms 兜底快照数据，避免接口等待外部爬虫计算
    """
    key = fields.CharField(max_length=128, pk=True, description="快照标识键，例如 chart:indices_comparison")
    payload = fields.JSONField(description="快照完整序列化 JSON 数据")
    created_at = fields.DatetimeField(auto_now_add=True, description="首次创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="最新更新时间")

    class Meta:
        table = "data_snapshots"

    def __str__(self):
        return f"DataSnapshot({self.key}, updated_at={self.updated_at})"
