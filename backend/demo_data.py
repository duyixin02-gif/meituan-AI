from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from merchant_ops_store import MerchantOpsStore


STYLE_TAGS = [
    ("style_001", ["裸色", "短甲", "通勤"], ["工作日", "低调精致"]),
    ("style_002", ["法式", "白色", "约会"], ["约会", "轻奢"]),
    ("style_003", ["猫眼", "低饱和", "高级感"], ["周末", "拍照"]),
    ("style_004", ["亮片", "派对", "长甲"], ["节日", "派对"]),
    ("style_005", ["粉色", "甜美", "短甲"], ["约会", "学生"]),
    ("style_006", ["渐变", "通勤", "低饱和"], ["工作日", "简约"]),
    ("style_007", ["红色", "节日", "显白"], ["节日", "聚会"]),
    ("style_008", ["黑色", "酷感", "长甲"], ["拍照", "个性"]),
]

USER_SEGMENTS = ["通勤白领", "学生党", "约会人群", "新娘备婚", "周末社交"]


def create_demo_records(count: int = 80) -> list[dict[str, Any]]:
    rng = random.Random(20260520)
    now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    merchants = ["merchant_001", "merchant_002", "merchant_003"]

    for index in range(max(1, min(count, 300))):
        merchant_id = merchants[index % len(merchants)]
        style_id, style_tags, scenario_tags = STYLE_TAGS[index % len(STYLE_TAGS)]
        days_ago = rng.randint(0, 13)
        trend_bonus = 1.5 if "通勤" in style_tags and days_ago <= 6 else 1.0
        click_count = int(rng.randint(8, 42) * trend_bonus)
        tryon_count = int(click_count * rng.uniform(0.18, 0.42))
        favorite_count = int(tryon_count * rng.uniform(0.18, 0.45))
        conversion_count = int(favorite_count * rng.uniform(0.08, 0.28))
        records.append(
            {
                "createdAt": (now - timedelta(days=days_ago, hours=rng.randint(0, 20))).isoformat(),
                "merchantId": merchant_id,
                "eventType": "campaign_candidate",
                "styleId": style_id,
                "sessionId": f"demo_session_{index:03d}",
                "userSegment": USER_SEGMENTS[index % len(USER_SEGMENTS)],
                "scenarioTags": scenario_tags,
                "styleTags": style_tags,
                "metrics": {
                    "clickCount": click_count,
                    "tryonCount": tryon_count,
                    "favoriteCount": favorite_count,
                    "conversionCount": conversion_count,
                },
                "notes": "demo merchant ops record",
            }
        )
    return records


def seed_demo_records(count: int = 80) -> dict[str, Any]:
    store = MerchantOpsStore()
    records = create_demo_records(count)
    stored = store.append_many(records)
    return {
        "ok": True,
        "storedCount": len(stored),
        "summary": store.summary(),
    }
