from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops_agent import OpsAnalyticsService


ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_ACTION_LOG = ROOT / "backend" / "data" / "office_assistant_actions.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class OfficeAssistantGateway:
    """Unified assistant protocol for OpenClaw and office-tool connectors."""

    def __init__(self, analytics: OpsAnalyticsService | None = None) -> None:
        self.analytics = analytics or OpsAnalyticsService()

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
            "intents": [
                "generate_strategy",
                "explain_strategy",
                "generate_campaign",
                "accept_strategy",
                "create_follow_up",
                "show_capabilities",
            ],
            "guardrails": [
                "external users must be mapped to one merchant before reading merchant data",
                "high-impact actions return a confirmable action instead of executing silently",
                "platform trend data is aggregated and privacy-thresholded",
            ],
        }

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = self._normalize_envelope(payload)
        intent = envelope["intent"] or self._infer_intent(envelope["message"])
        if intent == "generate_strategy":
            return self.generate_strategy(envelope)
        if intent == "explain_strategy":
            return self.explain_strategy(envelope)
        if intent == "generate_campaign":
            return self.generate_campaign(envelope)
        if intent == "accept_strategy":
            return self.accept_strategy(envelope)
        if intent == "create_follow_up":
            return self.create_follow_up(envelope)
        return self.show_capabilities(envelope)

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
        campaign = {
            "title": f"{tag}美甲试戴专场",
            "styleId": style_id,
            "targetAudience": f"近 {envelope['windowDays']} 天对 {tag} 有点击、收藏或试戴行为的用户",
            "placements": ["店铺首页主推", "团购套餐入口", "试戴推荐位"],
            "copies": [
                f"今天主推 {style_id}，先 AI 试戴再到店确认甲型。",
                f"{tag}风格近期热度上升，适合做短周期曝光和预约转化测试。",
                f"收藏过相关款式的用户可领取限时试戴优惠，到店后再确认设计细节。",
            ],
            "risk": "建议先跑 3 天小流量观察，结合库存、服务时长和客单价复核。",
        }
        return self._response(
            envelope,
            intent="generate_campaign",
            text=f"已生成「{campaign['title']}」，主推 {style_id}，建议先做 3 天观察。",
            data={"campaign": campaign},
            cards=[self._campaign_card(campaign)],
            actions=[self._confirmable_action("accept_strategy", "确认执行", envelope)],
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
            text="我可以生成策略、解释推荐原因、生成活动文案、记录采纳动作，并为多办公工具保留统一响应格式。",
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
        lowered = message.lower()
        if any(word in message for word in ["采纳", "确认执行", "执行这个"]) or "accept" in lowered:
            return "accept_strategy"
        if any(word in message for word in ["文案", "活动", "campaign"]) or "copy" in lowered:
            return "generate_campaign"
        if any(word in message for word in ["为什么", "解释", "原因", "explain", "why"]):
            return "explain_strategy"
        if any(word in message for word in ["提醒", "复盘", "follow"]):
            return "create_follow_up"
        if any(word in message for word in ["策略", "主推", "推荐", "strategy"]):
            return "generate_strategy"
        return "show_capabilities"

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
                {"label": "投放位置", "value": "、".join(campaign["placements"])},
            ],
            "copies": campaign["copies"],
            "risk": campaign["risk"],
        }

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
