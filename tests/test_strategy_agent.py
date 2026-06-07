from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from ops_agent import OpenClawStrategyAdapter, PromotionStrategyTool, SafetyReviewAgent, StrategyAgent
from strategy_schema import STRATEGY_SCHEMA_VERSION, StrategySignal, validate_strategy_recommendation
from strategy_scoring import StrategyScoringEngine


class StrategyAgentTest(unittest.TestCase):
    def test_scoring_engine_preserves_existing_style_ranking(self) -> None:
        styles = [
            {"styleId": "style_a", "clickGrowthRate": 0.2, "tryonRate": 0.9, "clickCount": 100},
            {"styleId": "style_b", "clickGrowthRate": 0.8, "tryonRate": 0.1, "clickCount": 10},
            {"styleId": "style_c", "clickGrowthRate": 0.8, "tryonRate": 0.3, "clickCount": 8},
            {"styleId": "style_d", "clickGrowthRate": 0.8, "tryonRate": 0.3, "clickCount": 20},
        ]

        ranked = StrategyScoringEngine().rank_styles(styles)

        self.assertEqual([item["styleId"] for item in ranked], ["style_d", "style_c", "style_b", "style_a"])

    def test_scoring_engine_preserves_existing_confidence_rules(self) -> None:
        scoring = StrategyScoringEngine()

        self.assertEqual(
            scoring.confidence(StrategySignal(kind="style", entityId="style_high", clickCount=30, tryonRate=0.2, clickGrowthRate=0.1)),
            "high",
        )
        self.assertEqual(
            scoring.confidence(StrategySignal(kind="style", entityId="style_medium", clickCount=10, tryonRate=0.1, clickGrowthRate=0.1)),
            "medium",
        )
        self.assertEqual(
            scoring.confidence(StrategySignal(kind="style", entityId="style_low", clickCount=9, tryonRate=0.9, clickGrowthRate=0.1)),
            "low",
        )

    def test_generates_featured_style_and_tag_campaign_with_stable_schema(self) -> None:
        dashboard = {
            "merchantId": "merchant_001",
            "windowDays": 7,
            "summary": {"clickGrowthRate": 0.42},
            "stylePerformance": [
                {
                    "styleId": "style_007",
                    "clickCount": 36,
                    "tryonRate": 0.25,
                    "clickGrowthRate": 0.8,
                    "styleTags": ["红色", "显白"],
                }
            ],
            "tagPerformance": [
                {
                    "tag": "红色",
                    "clickCount": 48,
                    "tryonRate": 0.2,
                    "clickGrowthRate": 0.7,
                }
            ],
        }
        platform = {
            "risingTags": [
                {
                    "tag": "红色",
                    "clickCount": 120,
                    "merchantCount": 3,
                    "clickGrowthRate": 0.6,
                }
            ]
        }

        recommendations = StrategyAgent().generate(dashboard, platform)

        self.assertEqual(
            [item["strategyType"] for item in recommendations],
            ["featured_style", "promotion_strategy", "tag_campaign"],
        )
        featured = recommendations[0]
        self.assertEqual(featured["schemaVersion"], STRATEGY_SCHEMA_VERSION)
        self.assertEqual(featured["title"], "设置试戴页主推款式")
        self.assertEqual(featured["action"]["styleId"], "style_007")
        self.assertEqual(featured["confidence"], "high")
        self.assertIn("平台匿名上升趋势", "".join(featured["reason"]))
        self.assertEqual(validate_strategy_recommendation(featured), [])

        promotion = recommendations[1]
        self.assertEqual(promotion["action"]["type"], "set_promotion_label")
        self.assertEqual(promotion["action"]["styleId"], "style_007")
        self.assertIn("promotionLabel", promotion["metadata"]["tool"])
        self.assertEqual(validate_strategy_recommendation(promotion), [])

        campaign = recommendations[2]
        self.assertEqual(campaign["action"]["tag"], "红色")
        self.assertEqual(validate_strategy_recommendation(campaign), [])

    def test_promotion_strategy_tool_generates_conversion_offer(self) -> None:
        result = PromotionStrategyTool().generate(
            style={
                "styleId": "style_009",
                "styleTags": ["猫眼"],
                "clickGrowthRate": 0.1,
                "tryonRate": 0.22,
                "conversionRate": 0.04,
            },
            top_tag={"tag": "猫眼"},
            platform_tags=[],
        )

        self.assertEqual(result["promotionLabel"], "试戴转化券")
        self.assertIn("立减", result["promotionOffer"])
        self.assertEqual(result["styleId"], "style_009")

    def test_generates_data_collection_when_no_signal_exists(self) -> None:
        recommendations = StrategyAgent().generate(
            {"stylePerformance": [], "tagPerformance": []},
            {"risingTags": []},
        )

        self.assertEqual(len(recommendations), 1)
        recommendation = recommendations[0]
        self.assertEqual(recommendation["strategyType"], "data_collection")
        self.assertEqual(recommendation["action"]["type"], "collect_more_events")
        self.assertEqual(recommendation["confidence"], "low")
        self.assertEqual(validate_strategy_recommendation(recommendation), [])

    def test_safety_review_blocks_cross_merchant_identifiers_and_keeps_schema_errors(self) -> None:
        unsafe = {
            "strategyType": "featured_style",
            "title": "参考其他商家 merchant_002 的主推",
            "action": {"type": "set_featured_style", "styleId": "style_001", "durationDays": 3},
            "reason": ["包含其他商家信息"],
            "risk": ["需要拦截"],
            "expectedMetric": {"primary": "tryonRate", "secondary": "favoriteRate"},
            "confidence": "high",
        }

        reviewed = SafetyReviewAgent().review([unsafe])[0]

        self.assertEqual(reviewed["schemaVersion"], STRATEGY_SCHEMA_VERSION)
        self.assertFalse(reviewed["safety"]["passed"])
        self.assertNotIn("schemaErrors", reviewed["safety"])

    def test_local_openclaw_fallback_adds_explanation_and_personalization(self) -> None:
        original_webhook = os.environ.pop("OPENCLAW_STRATEGY_WEBHOOK_URL", None)
        try:
            recommendation = StrategyAgent().generate(
                {
                    "merchantId": "merchant_001",
                    "summary": {"clickGrowthRate": 0.2},
                    "stylePerformance": [
                        {
                            "styleId": "style_008",
                            "clickCount": 20,
                            "tryonRate": 0.2,
                            "clickGrowthRate": 0.5,
                            "styleTags": ["黑色"],
                        }
                    ],
                    "tagPerformance": [],
                },
                {"risingTags": []},
            )

            assistant = OpenClawStrategyAdapter().generate(
                {
                    "merchantId": "merchant_001",
                    "windowDays": 7,
                    "dashboard": {
                        "summary": {"clickGrowthRate": 0.2},
                        "tagPerformance": [{"tag": "黑色"}],
                    },
                    "platformTrends": {"risingTags": []},
                    "recommendations": recommendation,
                }
            )
        finally:
            if original_webhook is not None:
                os.environ["OPENCLAW_STRATEGY_WEBHOOK_URL"] = original_webhook

        self.assertFalse(assistant["ai"]["enabled"])
        self.assertEqual(assistant["ai"]["mode"], "local-explainable-fallback")
        enriched = assistant["recommendations"][0]
        self.assertIn("assistantExplanation", enriched)
        self.assertIn("merchantPersonalization", enriched)
        self.assertIn("explainability", enriched)


if __name__ == "__main__":
    unittest.main()
