#!/usr/bin/env python
"""
刷新中国市场一级行业成分股映射。

用途:
- 低频更新本地 `股票 -> 一级行业` 映射
- 让中国市场热力图运行时不依赖在线行业列表接口
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.modules.market_cn.leaders import CNMarketLeaders


def main() -> int:
    sector_members = CNMarketLeaders._get_sector_members_map(force_refresh=True)
    if not sector_members:
        print("刷新失败: 未获取到任何一级行业成分股映射")
        return 1

    print(
        "刷新完成:",
        f"sectors={len(sector_members)}",
        f"source={CNMarketLeaders._sector_members_source}",
        f"file={CNMarketLeaders.SECTOR_MEMBERS_FILE}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
