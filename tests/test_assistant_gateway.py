from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from assistant_gateway import OfficeAssistantGateway


class OfficeAssistantGatewayTest(unittest.TestCase):
    def test_capabilities_include_clean_data_intent(self) -> None:
        capabilities = OfficeAssistantGateway().capabilities()

        self.assertIn("clean_data", capabilities["intents"])

    def test_clean_data_intent_runs_data_agent_and_returns_follow_up_action(self) -> None:
        summary = {
            "ok": True,
            "input": {
                "rawEventCount": 5,
                "cleanStyleEventCount": 3,
            },
            "output": {
                "newFeatureRecords": 2,
            },
        }
        with patch("assistant_gateway.DataAgentOrchestrator") as orchestrator:
            orchestrator.return_value.run.return_value = summary

            response = OfficeAssistantGateway().handle_message(
                {
                    "channel": "merchant-dashboard",
                    "externalUserId": "user_001",
                    "merchantId": "merchant_001",
                    "intent": "clean_data",
                    "message": "先清洗数据",
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["intent"], "clean_data")
        self.assertEqual(response["data"]["dataAgentSummary"], summary)
        self.assertEqual(response["reply"]["actions"][0]["intent"], "generate_strategy")

    def test_sales_question_routes_to_sales_agent_with_metric_boundary(self) -> None:
        dashboard = {
            "merchantId": "merchant_001",
            "windowDays": 1,
            "summary": {
                "clickCount": 100,
                "tryonCount": 40,
                "favoriteCount": 12,
                "conversionCount": 8,
                "conversionRate": 0.08,
                "conversionGrowthRate": 0.2,
            },
            "stylePerformance": [
                {
                    "styleId": "style_007",
                    "clickCount": 50,
                    "tryonCount": 20,
                    "conversionCount": 6,
                    "conversionRate": 0.12,
                    "styleTags": ["红色", "显白"],
                },
                {
                    "styleId": "style_003",
                    "clickCount": 30,
                    "tryonCount": 5,
                    "conversionCount": 0,
                    "conversionRate": 0.0,
                    "styleTags": ["猫眼"],
                },
            ],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics:
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "今天销售额怎么样？",
                    "merchantId": "merchant_001",
                }
            )

        analysis = response["data"]["salesAnalysis"]
        self.assertEqual(response["intent"], "query_sales_data")
        self.assertEqual(response["data"]["intentPlan"]["primaryIntent"], "query_sales_data")
        self.assertEqual(analysis["metricFocus"], "revenue")
        self.assertIn("salesAmount", analysis["dataScope"]["unavailableMetrics"])
        self.assertIn("不能直接回答营收金额", response["reply"]["text"])
        self.assertEqual(response["reply"]["cards"][0]["topStyles"][0]["styleId"], "style_007")

    def test_sales_question_extracts_week_window_and_top_selling_focus(self) -> None:
        dashboard = {
            "merchantId": "merchant_001",
            "windowDays": 7,
            "summary": {
                "clickCount": 80,
                "tryonCount": 20,
                "favoriteCount": 10,
                "conversionCount": 4,
                "conversionRate": 0.05,
                "conversionGrowthRate": -0.1,
            },
            "stylePerformance": [
                {
                    "styleId": "style_002",
                    "clickCount": 20,
                    "tryonCount": 8,
                    "conversionCount": 4,
                    "conversionRate": 0.2,
                    "styleTags": ["法式"],
                }
            ],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics:
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "本周哪款卖得最好？",
                    "merchantId": "merchant_001",
                }
            )

        slots = response["data"]["intentPlan"]["intents"][0]["slots"]
        self.assertEqual(response["intent"], "query_sales_data")
        self.assertEqual(slots["windowDays"], 7)
        self.assertEqual(slots["metricFocus"], "top_selling_styles")
        self.assertEqual(response["data"]["salesAnalysis"]["topStyles"][0]["styleId"], "style_002")

    def test_infers_clean_data_from_message(self) -> None:
        with patch("assistant_gateway.DataAgentOrchestrator") as orchestrator:
            orchestrator.return_value.run.return_value = {
                "ok": True,
                "input": {"rawEventCount": 1, "cleanStyleEventCount": 1},
                "output": {"newFeatureRecords": 1},
            }

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "帮我清洗一下数据",
                    "merchantId": "merchant_001",
                }
            )

        self.assertEqual(response["intent"], "clean_data")
        self.assertEqual(response["data"]["intentPlan"]["primaryIntent"], "clean_data")

    def test_splits_campaign_and_follow_up_intents_with_slots(self) -> None:
        dashboard = {
            "stylePerformance": [{"styleId": "style_007"}],
            "tagPerformance": [{"tag": "法式"}],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics, patch(
            "assistant_gateway.append_jsonl"
        ):
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "帮我生成今天企微群发文案，三天后提醒我复盘",
                    "merchantId": "merchant_001",
                }
            )

        plan = response["data"]["intentPlan"]
        self.assertEqual(response["intent"], "generate_campaign")
        self.assertEqual([step["intent"] for step in plan["intents"]], ["generate_campaign", "create_follow_up"])
        self.assertEqual(plan["intents"][0]["slots"]["channel"], "wecom")
        self.assertEqual(plan["intents"][0]["slots"]["copyType"], "群发文案")
        self.assertEqual(plan["intents"][1]["slots"]["followUpAfterDays"], 3)
        self.assertEqual(len(response["data"]["agentResults"]), 2)

    def test_extracts_style_tag_channel_and_tone_for_campaign(self) -> None:
        dashboard = {
            "stylePerformance": [{"styleId": "style_001"}],
            "tagPerformance": [{"tag": "高意向"}],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics:
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "围绕法式生成飞书活动文案，语气专业一点，主推 style_007",
                    "merchantId": "merchant_001",
                }
            )

        slots = response["data"]["intentPlan"]["intents"][0]["slots"]
        self.assertEqual(response["intent"], "generate_campaign")
        self.assertEqual(slots["tag"], "法式")
        self.assertEqual(slots["channel"], "feishu")
        self.assertEqual(slots["copyType"], "活动文案")
        self.assertEqual(slots["tone"], "专业")
        self.assertEqual(slots["styleId"], "style_007")
        self.assertEqual(response["data"]["campaign"]["styleId"], "style_007")
        self.assertEqual(response["data"]["campaign"]["title"], "法式美甲试戴专场")
        self.assertIn("platformBriefs", response["data"]["campaign"])

    def test_campaign_agent_returns_platform_prompts_and_publish_actions(self) -> None:
        dashboard = {
            "stylePerformance": [{"styleId": "style_007"}],
            "tagPerformance": [{"tag": "法式"}],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics:
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "生成今天小红书和抖音运营文案",
                    "merchantId": "merchant_001",
                }
            )

        campaign = response["data"]["campaign"]
        self.assertEqual(response["intent"], "generate_campaign")
        self.assertEqual([item["platform"] for item in campaign["platformBriefs"]], ["xiaohongshu", "douyin"])
        self.assertIn("小红书", campaign["platformBriefs"][0]["prompt"])
        self.assertIn("抖音", campaign["platformBriefs"][1]["prompt"])
        self.assertEqual([action["intent"] for action in response["reply"]["actions"][:2]], ["publish_campaign", "publish_campaign"])

    def test_revise_campaign_uses_revision_instruction(self) -> None:
        dashboard = {
            "stylePerformance": [{"styleId": "style_007"}],
            "tagPerformance": [{"tag": "法式"}],
        }
        with patch("assistant_gateway.OpsAnalyticsService") as analytics:
            analytics.return_value.merchant_dashboard.return_value = dashboard

            response = OfficeAssistantGateway().handle_message(
                {
                    "message": "把小红书文案改得更高端一点",
                    "merchantId": "merchant_001",
                    "context": {
                        "styleId": "style_007",
                        "tag": "法式",
                    },
                }
            )

        campaign = response["data"]["campaign"]
        self.assertEqual(response["intent"], "generate_campaign")
        self.assertEqual(response["data"]["intentPlan"]["primaryIntent"], "revise_campaign")
        self.assertEqual(campaign["revision"]["status"], "revised")
        self.assertIn("更高端", campaign["revision"]["instruction"])
        self.assertEqual([item["platform"] for item in campaign["platformCopies"]], ["xiaohongshu"])

    def test_publish_campaign_returns_pending_confirmation_plan(self) -> None:
        response = OfficeAssistantGateway().handle_message(
            {
                "message": "发布到小红书和微博",
                "merchantId": "merchant_001",
            }
        )

        self.assertEqual(response["intent"], "publish_campaign")
        self.assertEqual(response["data"]["publishPlan"]["status"], "pending_confirmation")
        self.assertEqual(
            [item["platform"] for item in response["data"]["publishPlan"]["platforms"]],
            ["xiaohongshu", "weibo"],
        )
        self.assertIn("不直接向外部平台发布", response["data"]["publishPlan"]["guardrails"][0])

    def test_ambiguous_message_returns_clarification_plan(self) -> None:
        response = OfficeAssistantGateway().handle_message(
            {
                "message": "帮我发一下",
                "merchantId": "merchant_001",
            }
        )

        self.assertEqual(response["intent"], "show_capabilities")
        self.assertTrue(response["data"]["intentPlan"]["requiresClarification"])
        self.assertIn("生成运营文案", response["reply"]["text"])


if __name__ == "__main__":
    unittest.main()
