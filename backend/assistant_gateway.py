from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from data_agent import DataAgentOrchestrator
from ops_agent import OpsAnalyticsService


ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_ACTION_LOG = ROOT / "backend" / "data" / "office_assistant_actions.jsonl"
BUSINESS_TIMEZONE = timezone(timedelta(hours=8))


SUPPORTED_INTENTS = [
    "query_sales_data",
    "generate_strategy",
    "clean_data",
    "explain_strategy",
    "generate_campaign",
    "revise_campaign",
    "publish_campaign",
    "accept_strategy",
    "create_follow_up",
    "show_capabilities",
]

SOCIAL_PLATFORM_GUIDES = {
    "xiaohongshu": {
        "label": "小红书",
        "style": "种草感、真实体验、强调显白/氛围/拍照效果，标题要有记忆点。",
        "format": "标题 + 3 条卖点 + 1 句到店/试戴 CTA。",
        "avoid": "避免夸大疗效、绝对化承诺和过度硬广。",
    },
    "douyin": {
        "label": "抖音",
        "style": "短视频口播感，开头要抓人，适合搭配试戴前后对比。",
        "format": "3 秒钩子 + 画面脚本 + 结尾 CTA。",
        "avoid": "避免长段落和复杂数据堆砌。",
    },
    "dianping": {
        "label": "大众点评",
        "style": "偏本地生活交易转化，突出套餐、到店体验、适合人群和预约理由。",
        "format": "活动标题 + 套餐/服务亮点 + 到店 CTA。",
        "avoid": "避免虚构折扣、虚构评价和无法兑现的服务承诺。",
    },
    "weibo": {
        "label": "微博",
        "style": "轻话题、适合扩散，保留短句和话题标签。",
        "format": "短文案 + 2 个话题标签 + CTA。",
        "avoid": "避免信息过密和过强销售感。",
    },
    "kuaishou": {
        "label": "快手",
        "style": "直接、接地气、强调到店可见和实用效果。",
        "format": "口语化推荐 + 适合人群 + 到店 CTA。",
        "avoid": "避免过度精英化表达和空泛高级感。",
    },
    "wechat_moments": {
        "label": "微信朋友圈",
        "style": "熟人社交语气，克制、自然、像门店日常推荐。",
        "format": "短句开场 + 款式亮点 + 私信/预约 CTA。",
        "avoid": "避免刷屏感、感叹号堆叠和强迫式转发。",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class IntentRouter:
    """Rule-based intent router with multi-intent planning and slot extraction."""

    INTENT_KEYWORDS = {
        "query_sales_data": [
            "销售",
            "销售额",
            "订单",
            "成交",
            "营收",
            "收入",
            "客单价",
            "卖得最好",
            "卖得",
            "sales",
            "revenue",
            "order",
        ],
        "accept_strategy": ["采纳", "确认执行", "执行这个", "accept"],
        "clean_data": ["清洗", "整理数据", "处理数据", "数据处理", "clean"],
        "publish_campaign": ["发布", "投放", "发到", "发去", "publish"],
        "revise_campaign": ["修改", "改一下", "改", "调整", "优化", "润色", "重写", "revision", "revise"],
        "generate_campaign": ["文案", "活动", "群发", "朋友圈", "campaign", "copy"],
        "explain_strategy": ["为什么", "解释", "原因", "explain", "why"],
        "create_follow_up": ["提醒", "复盘", "follow"],
        "generate_strategy": ["策略", "主推哪", "推荐哪", "推荐一下", "推荐策略", "strategy"],
    }
    CHANNEL_ALIASES = {
        "飞书": "feishu",
        "钉钉": "dingtalk",
        "企微": "wecom",
        "企业微信": "wecom",
        "微信": "wecom",
        "slack": "slack",
        "teams": "teams",
        "邮件": "email",
        "email": "email",
    }
    SOCIAL_PLATFORM_ALIASES = {
        "小红书": "xiaohongshu",
        "红书": "xiaohongshu",
        "抖音": "douyin",
        "大众点评": "dianping",
        "点评": "dianping",
        "微博": "weibo",
        "快手": "kuaishou",
        "微信朋友圈": "wechat_moments",
        "朋友圈": "wechat_moments",
    }
    CHINESE_NUMBERS = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }

    def parse(self, envelope: dict[str, Any]) -> dict[str, Any]:
        message = envelope["message"]
        base_slots = self._extract_slots(message, envelope)
        explicit_intent = envelope["intent"]
        if explicit_intent:
            return self._plan(
                [{"intent": explicit_intent, "confidence": 1.0, "slots": base_slots}],
                explicit=True,
            )

        detected = self._detect_intents(message, base_slots)
        if detected:
            return self._plan(detected, explicit=False)
        if message:
            return {
                "primaryIntent": "show_capabilities",
                "intents": [],
                "requiresClarification": True,
                "clarificationQuestion": "你是想生成策略、生成运营文案、解释推荐原因，还是创建复盘提醒？",
                "slots": base_slots,
            }
        return self._plan([{"intent": "show_capabilities", "confidence": 0.5, "slots": base_slots}], explicit=False)

    def _plan(self, intents: list[dict[str, Any]], explicit: bool) -> dict[str, Any]:
        safe_intents = [
            item
            for item in intents
            if item.get("intent") in SUPPORTED_INTENTS and isinstance(item.get("slots"), dict)
        ]
        if not safe_intents:
            safe_intents = [{"intent": "show_capabilities", "confidence": 0.5, "slots": {}}]
        return {
            "primaryIntent": safe_intents[0]["intent"],
            "intents": safe_intents,
            "requiresClarification": False,
            "clarificationQuestion": "",
            "explicitIntent": explicit,
        }

    def _detect_intents(self, message: str, slots: dict[str, Any]) -> list[dict[str, Any]]:
        lowered = message.lower()
        matches = []
        for intent, keywords in self.INTENT_KEYWORDS.items():
            positions = [self._keyword_position(message, lowered, keyword) for keyword in keywords]
            positions = [position for position in positions if position >= 0]
            if not positions:
                continue
            confidence = 0.9 if intent in {"accept_strategy", "clean_data"} else 0.82
            if len(positions) > 1:
                confidence += 0.05
            matches.append(
                {
                    "intent": intent,
                    "confidence": round(min(confidence, 0.98), 2),
                    "slots": dict(slots),
                    "position": min(positions),
                }
            )

        matches.sort(key=lambda item: item["position"])
        matched_intents = {item["intent"] for item in matches}
        if "revise_campaign" in matched_intents or "publish_campaign" in matched_intents:
            matches = [item for item in matches if item["intent"] != "generate_campaign"]
        return [{key: value for key, value in item.items() if key != "position"} for item in matches]

    def _keyword_position(self, message: str, lowered: str, keyword: str) -> int:
        if keyword.isascii():
            return lowered.find(keyword.lower())
        return message.find(keyword)

    def _extract_slots(self, message: str, envelope: dict[str, Any]) -> dict[str, Any]:
        slots: dict[str, Any] = {}
        if not message:
            return slots

        slots.update(self._extract_time_slots(message))
        channel = self._extract_channel(message)
        if channel:
            slots["channel"] = channel
        style_id = self._extract_style_id(message)
        if style_id:
            slots["styleId"] = style_id
        tag = self._extract_tag(message)
        if tag:
            slots["tag"] = tag
        copy_type = self._extract_copy_type(message)
        if copy_type:
            slots["copyType"] = copy_type
        tone = self._extract_tone(message)
        if tone:
            slots["tone"] = tone
        platforms = self._extract_social_platforms(message)
        if platforms:
            slots["targetPlatforms"] = platforms
        revision = self._extract_revision_instruction(message)
        if revision:
            slots["revisionInstruction"] = revision
        if "windowDays" not in slots and envelope.get("windowDays"):
            slots["windowDays"] = envelope["windowDays"]
        metric_focus = self._extract_metric_focus(message)
        if metric_focus:
            slots["metricFocus"] = metric_focus
        return slots

    def _extract_time_slots(self, message: str) -> dict[str, Any]:
        slots: dict[str, Any] = {}
        if "今天" in message:
            slots["businessDate"] = datetime.now(BUSINESS_TIMEZONE).date().isoformat()
            slots["dateReference"] = "today"
            slots["windowDays"] = 1
        elif "明天" in message:
            slots["dateReference"] = "tomorrow"
        elif "本周" in message:
            slots["windowDays"] = 7
        elif "本月" in message:
            slots["windowDays"] = 30

        window_match = re.search(r"近\s*(\d{1,2})\s*天", message)
        if window_match:
            slots["windowDays"] = max(1, min(int(window_match.group(1)), 90))

        follow_up_match = re.search(r"(\d{1,2}|[一二两三四五六七八九十])\s*天后", message)
        if follow_up_match:
            slots["followUpAfterDays"] = self._parse_small_number(follow_up_match.group(1))
        return slots

    def _extract_channel(self, message: str) -> str:
        lowered = message.lower()
        for alias, channel in self.CHANNEL_ALIASES.items():
            if alias.isascii():
                if alias.lower() in lowered:
                    return channel
            elif alias in message:
                return channel
        return ""

    def _extract_style_id(self, message: str) -> str:
        match = re.search(r"style[_-]\d{1,4}", message, re.IGNORECASE)
        return match.group(0).replace("-", "_").lower() if match else ""

    def _extract_social_platforms(self, message: str) -> list[str]:
        platforms = []
        for alias, platform in self.SOCIAL_PLATFORM_ALIASES.items():
            if alias in message and platform not in platforms:
                platforms.append(platform)
        return platforms

    def _extract_tag(self, message: str) -> str:
        patterns = [
            r"围绕(.{1,12}?)(?:生成|做|写|出|的)",
            r"把(.{1,12}?)(?:款|风格).{0,8}?(?:生成|做|写|出)",
            r"(.{1,8}?)(?:款|风格).{0,8}?(?:文案|活动|群发)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if not match:
                continue
            tag = match.group(1).strip(" ，,。的")
            if tag and not any(word in tag for word in ["帮我", "今天", "生成"]):
                return tag
        return ""

    def _extract_copy_type(self, message: str) -> str:
        if "朋友圈" in message:
            return "朋友圈文案"
        if "群发" in message:
            return "群发文案"
        if "活动" in message:
            return "活动文案"
        if "运营文案" in message:
            return "运营文案"
        if "文案" in message:
            return "文案"
        return ""

    def _extract_tone(self, message: str) -> str:
        tones = ["专业", "轻促销", "活泼", "高端", "温柔", "简洁"]
        found = [tone for tone in tones if tone in message]
        return "、".join(found)

    def _extract_revision_instruction(self, message: str) -> str:
        if any(word in message for word in ["修改", "改一下", "改", "调整", "优化", "润色", "重写"]):
            return message
        return ""

    def _extract_metric_focus(self, message: str) -> str:
        if any(word in message for word in ["销售额", "营收", "收入", "revenue"]):
            return "revenue"
        if any(word in message for word in ["订单", "成交", "order"]):
            return "orders"
        if any(word in message for word in ["客单价"]):
            return "average_order_value"
        if any(word in message for word in ["卖得最好", "卖得", "热卖"]):
            return "top_selling_styles"
        if any(word in message for word in ["转化"]):
            return "conversion"
        return ""

    def _parse_small_number(self, value: str) -> int:
        if value.isdigit():
            return max(1, min(int(value), 90))
        return self.CHINESE_NUMBERS.get(value, 3)


class SalesDataAgent:
    """Answers sales-data questions from available merchant analytics.

    The current data model has no real order amount field, so this agent reports
    conversion metrics as a sales proxy and keeps revenue fields explicit.
    """

    def analyze(
        self,
        dashboard: dict[str, Any],
        question: str,
        slots: dict[str, Any],
    ) -> dict[str, Any]:
        summary = dashboard.get("summary", {})
        styles = dashboard.get("stylePerformance") or []
        metric_focus = slots.get("metricFocus") or "sales_overview"
        top_styles = self._top_styles(styles)
        low_conversion_styles = self._low_conversion_styles(styles)
        unavailable_metrics = ["salesAmount", "orderAmount", "averageOrderValue"]
        analysis = {
            "question": question,
            "metricFocus": metric_focus,
            "windowDays": dashboard.get("windowDays"),
            "merchantId": dashboard.get("merchantId"),
            "dataScope": {
                "source": "merchant_dashboard",
                "availableMetrics": [
                    "clickCount",
                    "tryonCount",
                    "favoriteCount",
                    "conversionCount",
                    "conversionRate",
                ],
                "unavailableMetrics": unavailable_metrics,
                "salesProxy": "conversionCount 表示预约/成交转化代理指标，不等同于真实销售额。",
            },
            "metrics": {
                "clickCount": summary.get("clickCount", 0),
                "tryonCount": summary.get("tryonCount", 0),
                "favoriteCount": summary.get("favoriteCount", 0),
                "conversionCount": summary.get("conversionCount", 0),
                "conversionRate": summary.get("conversionRate", 0),
                "conversionGrowthRate": summary.get("conversionGrowthRate", 0),
            },
            "topStyles": top_styles,
            "lowConversionStyles": low_conversion_styles,
            "recommendations": self._recommendations(metric_focus, top_styles, low_conversion_styles),
            "rewriteBrief": {
                "role": "OpenClaw sales analyst",
                "tone": "准确、克制、运营视角，必须说明当前没有真实销售额字段。",
                "mustMention": [
                    "当前回答基于转化代理指标",
                    "不要把 conversionCount 说成真实销售额",
                    "如果需要销售额，需要接入订单金额/支付数据",
                ],
            },
        }
        analysis["summaryText"] = self._summary_text(analysis)
        return analysis

    def _top_styles(self, styles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = sorted(
            styles,
            key=lambda item: (
                float(item.get("conversionCount") or 0),
                float(item.get("conversionRate") or 0),
                float(item.get("tryonCount") or 0),
            ),
            reverse=True,
        )
        return [self._style_snapshot(item) for item in ranked[:3]]

    def _low_conversion_styles(self, styles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = [
            item
            for item in styles
            if float(item.get("clickCount") or 0) > 0 and float(item.get("conversionRate") or 0) <= 0.05
        ]
        ranked = sorted(candidates, key=lambda item: float(item.get("clickCount") or 0), reverse=True)
        return [self._style_snapshot(item) for item in ranked[:3]]

    def _style_snapshot(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "styleId": item.get("styleId"),
            "clickCount": item.get("clickCount", 0),
            "tryonCount": item.get("tryonCount", 0),
            "conversionCount": item.get("conversionCount", 0),
            "conversionRate": item.get("conversionRate", 0),
            "styleTags": item.get("styleTags", []),
        }

    def _recommendations(
        self,
        metric_focus: str,
        top_styles: list[dict[str, Any]],
        low_conversion_styles: list[dict[str, Any]],
    ) -> list[str]:
        recommendations = []
        if top_styles:
            recommendations.append(f"优先复核 {top_styles[0]['styleId']} 的库存、排期和活动入口。")
        if low_conversion_styles:
            recommendations.append(f"检查 {low_conversion_styles[0]['styleId']} 是否存在曝光高但预约转化低的问题。")
        if metric_focus in {"revenue", "average_order_value"}:
            recommendations.append("如需回答销售额或客单价，需要接入订单金额、支付状态和退款数据。")
        if not recommendations:
            recommendations.append("当前样本不足，建议先补齐点击、试戴、预约和订单数据。")
        return recommendations

    def _summary_text(self, analysis: dict[str, Any]) -> str:
        metrics = analysis["metrics"]
        top_styles = analysis["topStyles"]
        top_style = top_styles[0]["styleId"] if top_styles else "暂无明确热卖款"
        return (
            f"近 {analysis['windowDays']} 天可用的销售代理指标显示："
            f"转化数 {metrics['conversionCount']}，转化率 {metrics['conversionRate']:.1%}，"
            f"转化增长 {metrics['conversionGrowthRate']:.1%}。"
            f"当前没有真实销售额/客单价字段，不能直接回答营收金额。"
            f"按转化代理指标看，优先关注 {top_style}。"
        )


class OfficeAssistantGateway:
    """Unified assistant protocol for OpenClaw and office-tool connectors."""

    def __init__(self, analytics: OpsAnalyticsService | None = None) -> None:
        self.analytics = analytics or OpsAnalyticsService()
        self.intent_router = IntentRouter()
        self.sales_agent = SalesDataAgent()

    def capabilities(self) -> dict[str, Any]:
        return {
            "ok": True,
            "protocol": "office-assistant-v1",
            "supportedChannels": [
                "openclaw",
                "feishu",
                "slack",
                "teams",
                "dingtalk",
                "wecom",
                "email",
                "merchant-dashboard",
            ],
            "supportedPublishPlatforms": [
                guide["label"] for guide in SOCIAL_PLATFORM_GUIDES.values()
            ],
            "intents": [
                *SUPPORTED_INTENTS,
            ],
            "guardrails": [
                "external users must be mapped to one merchant before reading merchant data",
                "high-impact actions return a confirmable action instead of executing silently",
                "platform trend data is aggregated and privacy-thresholded",
                "sales questions currently use conversion metrics unless real order amount data is connected",
            ],
        }

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = self._normalize_envelope(payload)
        plan = self.intent_router.parse(envelope)
        if plan.get("requiresClarification"):
            return self._response(
                envelope,
                intent="show_capabilities",
                text=plan["clarificationQuestion"],
                data={"intentPlan": plan},
            )
        results = [self._dispatch_intent(envelope, step) for step in plan["intents"]]
        if len(results) == 1:
            response = results[0]
            response["data"]["intentPlan"] = plan
            return response
        return self._compose_multi_intent_response(envelope, plan, results)

    def _dispatch_intent(self, envelope: dict[str, Any], step: dict[str, Any]) -> dict[str, Any]:
        intent = step["intent"]
        step_envelope = {
            **envelope,
            "intent": intent,
            "context": {
                **envelope["context"],
                **step.get("slots", {}),
            },
        }
        if "windowDays" in step.get("slots", {}):
            step_envelope["windowDays"] = self._safe_window(step["slots"]["windowDays"])
        if intent == "query_sales_data":
            return self.query_sales_data(step_envelope)
        if intent == "clean_data":
            return self.clean_data(step_envelope)
        if intent == "generate_strategy":
            return self.generate_strategy(step_envelope)
        if intent == "explain_strategy":
            return self.explain_strategy(step_envelope)
        if intent == "generate_campaign":
            return self.generate_campaign(step_envelope)
        if intent == "revise_campaign":
            return self.revise_campaign(step_envelope)
        if intent == "publish_campaign":
            return self.publish_campaign(step_envelope)
        if intent == "accept_strategy":
            return self.accept_strategy(step_envelope)
        if intent == "create_follow_up":
            return self.create_follow_up(step_envelope)
        return self.show_capabilities(step_envelope)

    def _compose_multi_intent_response(
        self,
        envelope: dict[str, Any],
        plan: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        text = "\n".join(result.get("reply", {}).get("text", "") for result in results if result.get("reply"))
        cards = []
        actions = []
        for result in results:
            reply = result.get("reply", {})
            cards.extend(reply.get("cards", []))
            actions.extend(reply.get("actions", []))
        return self._response(
            envelope,
            intent=plan["primaryIntent"],
            text=text,
            data={"intentPlan": plan, "agentResults": results},
            cards=cards,
            actions=actions,
        )

    def clean_data(self, envelope: dict[str, Any]) -> dict[str, Any]:
        summary = DataAgentOrchestrator().run()
        input_stats = summary.get("input", {})
        output_stats = summary.get("output", {})
        text = (
            f"已完成数据清洗：读取 {input_stats.get('rawEventCount', 0)} 条原始事件，"
            f"保留 {input_stats.get('cleanStyleEventCount', 0)} 条有效款式行为，"
            f"新增 {output_stats.get('newFeatureRecords', 0)} 条结构化特征记录。"
        )
        return self._response(
            envelope,
            intent="clean_data",
            text=text,
            data={"dataAgentSummary": summary},
            actions=[self._confirmable_action("generate_strategy", "基于清洗结果生成策略", envelope)],
        )

    def query_sales_data(self, envelope: dict[str, Any]) -> dict[str, Any]:
        dashboard = self.analytics.merchant_dashboard(envelope["merchantId"], envelope["windowDays"])
        analysis = self.sales_agent.analyze(dashboard, envelope["message"], envelope["context"])
        return self._response(
            envelope,
            intent="query_sales_data",
            text=analysis["summaryText"],
            data={"salesAnalysis": analysis},
            cards=[self._sales_card(analysis)],
            actions=[
                self._confirmable_action("generate_strategy", "基于转化数据生成策略", envelope),
                self._confirmable_action("generate_campaign", "生成转化提升文案", envelope),
            ],
        )

    def generate_strategy(self, envelope: dict[str, Any]) -> dict[str, Any]:
        strategy = self.analytics.generate_strategy(envelope["merchantId"], envelope["windowDays"])
        cards = [self._strategy_card(item) for item in strategy.get("recommendations", [])]
        return self._response(
            envelope,
            intent="generate_strategy",
            text=self._strategy_text(strategy),
            data={"strategy": strategy},
            cards=cards,
            actions=[
                self._confirmable_action("accept_strategy", "采纳策略", envelope),
                self._confirmable_action("generate_campaign", "生成活动文案", envelope),
            ],
        )

    def explain_strategy(self, envelope: dict[str, Any]) -> dict[str, Any]:
        strategy = self.analytics.generate_strategy(envelope["merchantId"], envelope["windowDays"])
        target_type = str(envelope["context"].get("strategyType") or "")
        recommendations = strategy.get("recommendations", [])
        item = next(
            (candidate for candidate in recommendations if candidate.get("strategyType") == target_type),
            recommendations[0] if recommendations else {},
        )
        explanation = item.get("assistantExplanation") or "当前策略由规则引擎排序，并由 OpenClaw 助手层补充解释。"
        return self._response(
            envelope,
            intent="explain_strategy",
            text=f"{item.get('title', '策略解释')}：{explanation}",
            data={"recommendation": item, "strategy": strategy},
            cards=[self._strategy_card(item)] if item else [],
            actions=[self._confirmable_action("generate_campaign", "转成活动文案", envelope)],
        )

    def generate_campaign(self, envelope: dict[str, Any]) -> dict[str, Any]:
        dashboard = self.analytics.merchant_dashboard(envelope["merchantId"], envelope["windowDays"])
        top_style = (dashboard.get("stylePerformance") or [{}])[0]
        top_tag = (dashboard.get("tagPerformance") or [{}])[0]
        style_id = str(envelope["context"].get("styleId") or top_style.get("styleId") or "style_candidate")
        tag = str(envelope["context"].get("tag") or top_tag.get("tag") or "高意向")
        business_date = str(
            envelope["context"].get("businessDate")
            or datetime.now(BUSINESS_TIMEZONE).date().isoformat()
        )
        copy_type = str(envelope["context"].get("copyType") or "运营文案")
        tone = str(envelope["context"].get("tone") or "专业、轻促销、适合美甲门店")
        revision_instruction = str(envelope["context"].get("revisionInstruction") or "").strip()
        target_platforms = self._safe_platforms(envelope["context"].get("targetPlatforms"))
        if not target_platforms:
            target_platforms = list(SOCIAL_PLATFORM_GUIDES)
        campaign = {
            "title": f"{tag}美甲试戴专场",
            "styleId": style_id,
            "tag": tag,
            "businessDate": business_date,
            "copyType": copy_type,
            "tone": tone,
            "targetAudience": f"近 {envelope['windowDays']} 天对 {tag} 有点击、收藏或试戴行为的用户",
            "placements": ["店铺首页主推", "团购套餐入口", "试戴推荐位"],
            "objective": "把近期高意向款式转成可审查、可修改、可发布的运营文案草稿。",
            "copies": [
                self._base_campaign_copy(style_id, tag, copy_type, tone),
                f"{tag}风格近期热度上升，建议先做短周期曝光，观察试戴、收藏和预约变化。",
                f"对相关款式感兴趣的用户，可以先 AI 试戴，再到店确认甲型和设计细节。",
            ],
            "revision": {
                "round": int(envelope["context"].get("revisionRound") or (2 if revision_instruction else 1)),
                "instruction": revision_instruction,
                "status": "revised" if revision_instruction else "draft",
            },
            "platformBriefs": [
                self._platform_brief(platform, style_id, tag, copy_type, tone, revision_instruction)
                for platform in target_platforms
            ],
            "platformCopies": [
                self._platform_copy(platform, style_id, tag, copy_type, tone, revision_instruction)
                for platform in target_platforms
            ],
            "reviewQuestions": [
                "文案语气是否符合门店日常运营风格？",
                "是否需要更偏种草、成交转化、短视频口播或熟人社交？",
                "是否需要指定发布平台或继续修改某个平台版本？",
            ],
            "risk": "建议先跑 3 天小流量观察，结合库存、服务时长和客单价复核。",
        }
        text = self._campaign_text(campaign)
        return self._response(
            envelope,
            intent="generate_campaign",
            text=text,
            data={"campaign": campaign},
            cards=[self._campaign_card(campaign)],
            actions=[
                *self._publish_actions(envelope, target_platforms),
                self._confirmable_action("revise_campaign", "继续修改文案", envelope),
            ],
        )

    def revise_campaign(self, envelope: dict[str, Any]) -> dict[str, Any]:
        context = {
            **envelope["context"],
            "revisionInstruction": envelope["context"].get("revisionInstruction") or envelope["message"],
            "revisionRound": int(envelope["context"].get("revisionRound") or 1) + 1,
        }
        return self.generate_campaign({**envelope, "context": context})

    def publish_campaign(self, envelope: dict[str, Any]) -> dict[str, Any]:
        target_platforms = self._safe_platforms(envelope["context"].get("targetPlatforms"))
        if not target_platforms:
            target_platforms = ["wechat_moments"]
        plan = {
            "status": "pending_confirmation",
            "platforms": [
                {
                    "platform": platform,
                    "label": SOCIAL_PLATFORM_GUIDES[platform]["label"],
                    "requiresReview": True,
                }
                for platform in target_platforms
            ],
            "guardrails": [
                "当前只生成发布计划，不直接向外部平台发布。",
                "发布前需要使用者确认最终文案、素材、价格和库存。",
            ],
        }
        labels = "、".join(item["label"] for item in plan["platforms"])
        return self._response(
            envelope,
            intent="publish_campaign",
            text=f"已准备 {labels} 的发布计划，等待你确认最终文案和素材后再执行。",
            data={"publishPlan": plan},
            actions=[self._confirmable_action("accept_strategy", "确认发布计划", envelope)],
        )

    def accept_strategy(self, envelope: dict[str, Any]) -> dict[str, Any]:
        record = {
            "acceptedAt": utc_now(),
            "channel": envelope["channel"],
            "externalUserId": envelope["externalUserId"],
            "merchantId": envelope["merchantId"],
            "intent": "accept_strategy",
            "context": envelope["context"],
            "message": envelope["message"],
        }
        append_jsonl(ASSISTANT_ACTION_LOG, record)
        return self._response(
            envelope,
            intent="accept_strategy",
            text="已记录采纳动作。后续可以把这个动作接到店铺主推位、活动配置或飞书多维表格复盘台账。",
            data={"accepted": record},
            actions=[self._confirmable_action("create_follow_up", "创建复盘提醒", envelope)],
        )

    def create_follow_up(self, envelope: dict[str, Any]) -> dict[str, Any]:
        record = {
            "createdAt": utc_now(),
            "channel": envelope["channel"],
            "externalUserId": envelope["externalUserId"],
            "merchantId": envelope["merchantId"],
            "intent": "create_follow_up",
            "followUpAfterDays": int(envelope["context"].get("followUpAfterDays") or 3),
            "context": envelope["context"],
        }
        append_jsonl(ASSISTANT_ACTION_LOG, record)
        return self._response(
            envelope,
            intent="create_follow_up",
            text=f"已创建 {record['followUpAfterDays']} 天后的策略复盘记录。正式接入办公工具后，可同步为飞书/Teams/Slack 提醒。",
            data={"followUp": record},
        )

    def show_capabilities(self, envelope: dict[str, Any]) -> dict[str, Any]:
        capabilities = self.capabilities()
        return self._response(
            envelope,
            intent="show_capabilities",
            text="我可以回答销售/转化数据问题、生成策略、解释推荐原因、生成活动文案、记录采纳动作，并为多办公工具保留统一响应格式。",
            data={"capabilities": capabilities},
        )

    def _normalize_envelope(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
        return {
            "channel": str(payload.get("channel") or "openclaw"),
            "externalUserId": str(payload.get("externalUserId") or payload.get("userId") or "anonymous"),
            "merchantId": str(payload.get("merchantId") or context.get("merchantId") or "merchant_001"),
            "intent": str(payload.get("intent") or "").strip(),
            "message": str(payload.get("message") or payload.get("text") or "").strip(),
            "locale": str(payload.get("locale") or "zh-CN"),
            "windowDays": self._safe_window(payload.get("windowDays") or context.get("windowDays") or 7),
            "conversationId": str(payload.get("conversationId") or context.get("conversationId") or ""),
            "context": context,
        }

    def _infer_intent(self, message: str) -> str:
        plan = self.intent_router.parse(
            {
                "intent": "",
                "message": message,
                "windowDays": 7,
            }
        )
        return plan["primaryIntent"]

    def _response(
        self,
        envelope: dict[str, Any],
        intent: str,
        text: str,
        data: dict[str, Any] | None = None,
        cards: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "protocol": "office-assistant-v1",
            "intent": intent,
            "channel": envelope["channel"],
            "merchantId": envelope["merchantId"],
            "conversationId": envelope["conversationId"],
            "reply": {
                "text": text,
                "cards": cards or [],
                "actions": actions or [],
            },
            "data": data or {},
            "audit": {
                "generatedAt": utc_now(),
                "externalUserId": envelope["externalUserId"],
                "requiresMerchantMapping": envelope["externalUserId"] == "anonymous",
            },
        }

    def _strategy_text(self, strategy: dict[str, Any]) -> str:
        recommendations = strategy.get("recommendations") or []
        if not recommendations:
            return "当前样本不足，建议先积累试戴、收藏和预约数据。"
        top = recommendations[0]
        title = top.get("title") or "策略建议"
        explanation = top.get("assistantExplanation") or "建议先做短周期观察。"
        return f"{title}。{explanation}"

    def _strategy_card(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "strategy",
            "title": item.get("title") or item.get("strategyType") or "策略建议",
            "subtitle": item.get("strategyType"),
            "fields": [
                {"label": "置信度", "value": item.get("confidence", "medium")},
                {"label": "观察指标", "value": item.get("expectedMetric", {}).get("primary", "clickRate")},
                {"label": "动作", "value": item.get("action", {})},
            ],
            "explanation": item.get("assistantExplanation"),
            "risk": item.get("risk", []),
        }

    def _campaign_card(self, campaign: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "campaign",
            "title": campaign["title"],
            "subtitle": campaign["targetAudience"],
            "fields": [
                {"label": "主推款", "value": campaign["styleId"]},
                {"label": "文案类型", "value": campaign.get("copyType", "运营文案")},
                {"label": "业务日期", "value": campaign.get("businessDate")},
                {"label": "投放位置", "value": "、".join(campaign["placements"])},
            ],
            "copies": campaign["copies"],
            "platformCopies": campaign.get("platformCopies", []),
            "reviewQuestions": campaign.get("reviewQuestions", []),
            "risk": campaign["risk"],
        }

    def _sales_card(self, analysis: dict[str, Any]) -> dict[str, Any]:
        metrics = analysis["metrics"]
        return {
            "type": "sales_analysis",
            "title": "销售/转化数据分析",
            "subtitle": analysis["dataScope"]["salesProxy"],
            "fields": [
                {"label": "观察窗口", "value": f"{analysis['windowDays']} 天"},
                {"label": "转化数", "value": metrics["conversionCount"]},
                {"label": "转化率", "value": metrics["conversionRate"]},
                {"label": "转化增长", "value": metrics["conversionGrowthRate"]},
            ],
            "topStyles": analysis["topStyles"],
            "lowConversionStyles": analysis["lowConversionStyles"],
            "recommendations": analysis["recommendations"],
            "rewriteBrief": analysis["rewriteBrief"],
        }

    def _safe_platforms(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        platforms = []
        for platform in value:
            normalized = str(platform)
            if normalized in SOCIAL_PLATFORM_GUIDES and normalized not in platforms:
                platforms.append(normalized)
        return platforms

    def _base_campaign_copy(self, style_id: str, tag: str, copy_type: str, tone: str) -> str:
        if "轻促销" in tone:
            return f"今天主推 {style_id}：{tag}风格热度上升，适合先试戴再预约，先做一轮轻量转化测试。"
        if "高端" in tone:
            return f"今日精选 {style_id}，以{tag}风格突出精致感，适合需要低调但有设计感的到店用户。"
        return f"今天主推 {style_id}，围绕{tag}风格生成{copy_type}，建议先 AI 试戴再到店确认细节。"

    def _platform_brief(
        self,
        platform: str,
        style_id: str,
        tag: str,
        copy_type: str,
        tone: str,
        revision_instruction: str,
    ) -> dict[str, Any]:
        guide = SOCIAL_PLATFORM_GUIDES[platform]
        prompt = (
            f"你是美甲门店运营助手。请为{guide['label']}生成{copy_type}。"
            f"主推款式：{style_id}；核心风格：{tag}；语气：{tone}。"
            f"平台风格：{guide['style']} 输出格式：{guide['format']} "
            f"禁用：{guide['avoid']} "
            "必须基于后端提供的商家数据，不虚构折扣、库存、价格或其他商家信息。"
        )
        if revision_instruction:
            prompt += f" 本轮修改意见：{revision_instruction}"
        return {
            "platform": platform,
            "label": guide["label"],
            "prompt": prompt,
            "styleGuide": guide["style"],
            "format": guide["format"],
            "avoid": guide["avoid"],
        }

    def _platform_copy(
        self,
        platform: str,
        style_id: str,
        tag: str,
        copy_type: str,
        tone: str,
        revision_instruction: str,
    ) -> dict[str, Any]:
        guide = SOCIAL_PLATFORM_GUIDES[platform]
        copy = {
            "xiaohongshu": [
                f"{tag}美甲今天可以先收藏",
                f"主推 {style_id}，适合想要{tag}氛围但不想盲选的用户。先 AI 试戴看手型效果，再到店确认细节。",
                f"亮点：{tag}、上手直观、适合短周期试戴观察。",
            ],
            "douyin": [
                f"3 秒看懂今天为什么推 {style_id}",
                f"镜头 1：展示{tag}风格试戴效果；镜头 2：对比不同手型；镜头 3：提醒到店前先试戴。",
                "结尾：想看自己的上手效果，可以先预约 AI 试戴。",
            ],
            "dianping": [
                f"{tag}美甲试戴专场",
                f"今日推荐 {style_id}，适合近期关注{tag}风格的到店用户。",
                "建议先试戴再预约，到店后确认甲型、长度和设计细节。",
            ],
            "weibo": [
                f"今天的门店主推是 {style_id}，{tag}风格适合先试戴再决定。",
                f"#{tag}美甲# #AI试戴# 想看上手效果可以先预约体验。",
            ],
            "kuaishou": [
                f"今天给大家看一款实用的{tag}美甲：{style_id}。",
                "先试戴，看顺眼再到店做，少踩雷，也更好跟美甲师沟通细节。",
            ],
            "wechat_moments": [
                f"今天店里主推 {style_id}。",
                f"{tag}风格最近关注度比较高，适合先用 AI 试戴看一下上手效果。",
                "想看的可以私信，先确认风格再预约到店。",
            ],
        }[platform]
        if revision_instruction:
            copy.append(f"已按修改意见调整：{revision_instruction}")
        return {
            "platform": platform,
            "label": guide["label"],
            "copy": copy,
            "tone": tone,
        }

    def _campaign_text(self, campaign: dict[str, Any]) -> str:
        platform_labels = "、".join(item["label"] for item in campaign.get("platformCopies", []))
        status = "已根据修改意见更新" if campaign.get("revision", {}).get("status") == "revised" else "已生成"
        return (
            f"{status}「{campaign['title']}」，主推 {campaign['styleId']}。"
            f"已准备 {platform_labels} 的平台化版本；你可以继续提出修改意见，"
            "也可以选择一个平台进入发布确认。"
        )

    def _publish_actions(self, envelope: dict[str, Any], platforms: list[str]) -> list[dict[str, Any]]:
        actions = []
        for platform in platforms:
            label = SOCIAL_PLATFORM_GUIDES[platform]["label"]
            action_envelope = {
                **envelope,
                "context": {
                    **envelope["context"],
                    "targetPlatforms": [platform],
                },
            }
            actions.append(self._confirmable_action("publish_campaign", f"发布到{label}", action_envelope))
        return actions

    def _confirmable_action(self, intent: str, label: str, envelope: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "confirm",
            "label": label,
            "intent": intent,
            "payload": {
                "channel": envelope["channel"],
                "externalUserId": envelope["externalUserId"],
                "merchantId": envelope["merchantId"],
                "windowDays": envelope["windowDays"],
                "context": envelope["context"],
            },
        }

    def _safe_window(self, value: Any) -> int:
        try:
            return max(1, min(int(value), 90))
        except (TypeError, ValueError):
            return 7
