from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from merchant_ops_store import MerchantOpsStore


ROOT = Path(__file__).resolve().parents[1]
OPS_STRATEGY_LOG = ROOT / "backend" / "data" / "merchant_strategy_recommendations.jsonl"
PLATFORM_MIN_MERCHANTS = 2
PLATFORM_MIN_EVENTS = 4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def metric(record: dict[str, Any], name: str) -> float:
    metrics = record.get("metrics")
    if not isinstance(metrics, dict):
        return 0.0
    value = metrics.get(name, 0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass(frozen=True)
class WindowedRecords:
    current: list[dict[str, Any]]
    previous: list[dict[str, Any]]
    all_records: list[dict[str, Any]]
    window_days: int


class OpsAnalyticsService:
    def __init__(self, store: MerchantOpsStore | None = None) -> None:
        self.store = store or MerchantOpsStore()

    def merchant_dashboard(self, merchant_id: str, window_days: int = 7) -> dict[str, Any]:
        windowed = self._window_records(
            [record for record in self.store.list_records(limit=0) if record.get("merchantId") == merchant_id],
            window_days,
        )
        return {
            "ok": True,
            "merchantId": merchant_id,
            "generatedAt": utc_now(),
            "windowDays": windowed.window_days,
            "summary": self._summary_cards(windowed.current, windowed.previous),
            "stylePerformance": self._style_performance(windowed.current, windowed.previous),
            "tagPerformance": self._tag_performance(windowed.current, windowed.previous),
            "eventTrend": self._event_trend(windowed.current),
            "recordsCount": len(windowed.current),
        }

    def platform_trends(self, window_days: int = 7) -> dict[str, Any]:
        windowed = self._window_records(self.store.list_records(limit=0), window_days)
        current = windowed.current
        previous = windowed.previous
        return {
            "ok": True,
            "generatedAt": utc_now(),
            "windowDays": windowed.window_days,
            "privacy": {
                "minMerchantCount": PLATFORM_MIN_MERCHANTS,
                "minEventCount": PLATFORM_MIN_EVENTS,
                "dataPolicy": "Only aggregated tag and scenario trends are exposed.",
            },
            "risingTags": self._platform_tag_trends(current, previous, "styleTags"),
            "risingScenarios": self._platform_tag_trends(current, previous, "scenarioTags"),
            "recordsCount": len(current),
        }

    def generate_strategy(self, merchant_id: str, window_days: int = 7) -> dict[str, Any]:
        dashboard = self.merchant_dashboard(merchant_id, window_days)
        platform = self.platform_trends(window_days)
        recommendations = StrategyAgent().generate(dashboard, platform)
        reviewed = SafetyReviewAgent().review(recommendations)
        assistant = OpenClawStrategyAdapter().generate(
            {
                "merchantId": merchant_id,
                "windowDays": window_days,
                "dashboard": dashboard,
                "platformTrends": platform,
                "recommendations": reviewed,
            }
        )
        enriched = SafetyReviewAgent().review(assistant.get("recommendations") or reviewed)
        assistant["recommendations"] = enriched
        payload = {
            "ok": True,
            "merchantId": merchant_id,
            "generatedAt": utc_now(),
            "windowDays": window_days,
            "dashboard": dashboard,
            "platformTrends": platform,
            "recommendations": enriched,
            "assistant": assistant,
            "ai": assistant.get("ai", OpenClawStrategyAdapter().status()),
        }
        append_jsonl(
            OPS_STRATEGY_LOG,
            {
                "merchantId": merchant_id,
                "generatedAt": payload["generatedAt"],
                "windowDays": window_days,
                "recommendations": enriched,
                "assistant": assistant.get("handoff"),
            },
        )
        return payload

    def _window_records(self, records: list[dict[str, Any]], window_days: int) -> WindowedRecords:
        safe_window = max(1, min(window_days, 90))
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=safe_window)
        previous_start = now - timedelta(days=safe_window * 2)

        current: list[dict[str, Any]] = []
        previous: list[dict[str, Any]] = []
        timeless: list[dict[str, Any]] = []
        for record in records:
            created_at = parse_datetime(str(record.get("createdAt") or ""))
            if created_at is None:
                timeless.append(record)
            elif created_at >= current_start:
                current.append(record)
            elif created_at >= previous_start:
                previous.append(record)

        if not current and records:
            current = records[-min(len(records), 200) :]
        return WindowedRecords(current=current, previous=previous, all_records=records, window_days=safe_window)

    def _summary_cards(self, current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> dict[str, Any]:
        current_metrics = self._metric_totals(current)
        previous_metrics = self._metric_totals(previous)
        current_tryon_rate = self._rate(current_metrics["tryonCount"], current_metrics["clickCount"])
        current_favorite_rate = self._rate(current_metrics["favoriteCount"], current_metrics["clickCount"])
        current_conversion_rate = self._rate(current_metrics["conversionCount"], current_metrics["clickCount"])
        previous_tryon_rate = self._rate(previous_metrics["tryonCount"], previous_metrics["clickCount"])
        previous_favorite_rate = self._rate(previous_metrics["favoriteCount"], previous_metrics["clickCount"])
        previous_conversion_rate = self._rate(previous_metrics["conversionCount"], previous_metrics["clickCount"])
        return {
            "clickCount": current_metrics["clickCount"],
            "tryonCount": current_metrics["tryonCount"],
            "favoriteCount": current_metrics["favoriteCount"],
            "conversionCount": current_metrics["conversionCount"],
            "previousClickCount": previous_metrics["clickCount"],
            "previousTryonCount": previous_metrics["tryonCount"],
            "previousFavoriteCount": previous_metrics["favoriteCount"],
            "previousConversionCount": previous_metrics["conversionCount"],
            "tryonRate": current_tryon_rate,
            "favoriteRate": current_favorite_rate,
            "conversionRate": current_conversion_rate,
            "previousTryonRate": previous_tryon_rate,
            "previousFavoriteRate": previous_favorite_rate,
            "previousConversionRate": previous_conversion_rate,
            "clickGrowthRate": self._growth(current_metrics["clickCount"], previous_metrics["clickCount"]),
            "tryonGrowthRate": self._growth(current_metrics["tryonCount"], previous_metrics["tryonCount"]),
            "favoriteGrowthRate": self._growth(
                current_metrics["favoriteCount"], previous_metrics["favoriteCount"]
            ),
            "conversionGrowthRate": self._growth(
                current_metrics["conversionCount"], previous_metrics["conversionCount"]
            ),
            "tryonRateDelta": round(current_tryon_rate - previous_tryon_rate, 4),
            "favoriteRateDelta": round(current_favorite_rate - previous_favorite_rate, 4),
            "conversionRateDelta": round(current_conversion_rate - previous_conversion_rate, 4),
        }

    def _metric_totals(self, records: list[dict[str, Any]]) -> dict[str, float]:
        return {
            "clickCount": sum(metric(record, "clickCount") for record in records),
            "tryonCount": sum(metric(record, "tryonCount") for record in records),
            "favoriteCount": sum(metric(record, "favoriteCount") for record in records),
            "conversionCount": sum(metric(record, "conversionCount") for record in records),
        }

    def _style_performance(
        self, current: list[dict[str, Any]], previous: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        previous_clicks = self._group_metric(previous, "styleId", "clickCount")
        style_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "styleId": "",
                "clickCount": 0.0,
                "tryonCount": 0.0,
                "favoriteCount": 0.0,
                "conversionCount": 0.0,
                "styleTags": Counter(),
                "scenarioTags": Counter(),
            }
        )
        for record in current:
            style_id = str(record.get("styleId") or "unknown")
            item = style_metrics[style_id]
            item["styleId"] = style_id
            item["clickCount"] += metric(record, "clickCount")
            item["tryonCount"] += metric(record, "tryonCount")
            item["favoriteCount"] += metric(record, "favoriteCount")
            item["conversionCount"] += metric(record, "conversionCount")
            item["styleTags"].update(record.get("styleTags", []))
            item["scenarioTags"].update(record.get("scenarioTags", []))

        result = []
        for style_id, item in style_metrics.items():
            clicks = item["clickCount"]
            result.append(
                {
                    "styleId": style_id,
                    "clickCount": round(clicks, 2),
                    "tryonCount": round(item["tryonCount"], 2),
                    "favoriteCount": round(item["favoriteCount"], 2),
                    "conversionCount": round(item["conversionCount"], 2),
                    "tryonRate": self._rate(item["tryonCount"], clicks),
                    "conversionRate": self._rate(item["conversionCount"], clicks),
                    "clickGrowthRate": self._growth(clicks, previous_clicks.get(style_id, 0.0)),
                    "styleTags": [tag for tag, _ in item["styleTags"].most_common(5)],
                    "scenarioTags": [tag for tag, _ in item["scenarioTags"].most_common(5)],
                }
            )
        return sorted(
            result,
            key=lambda item: (item["clickGrowthRate"], item["tryonRate"], item["clickCount"]),
            reverse=True,
        )[:12]

    def _tag_performance(
        self, current: list[dict[str, Any]], previous: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        previous_clicks = self._tag_metric(previous, "styleTags", "clickCount")
        current_clicks = self._tag_metric(current, "styleTags", "clickCount")
        current_tryons = self._tag_metric(current, "styleTags", "tryonCount")
        result = []
        for tag, clicks in current_clicks.items():
            result.append(
                {
                    "tag": tag,
                    "clickCount": round(clicks, 2),
                    "tryonCount": round(current_tryons.get(tag, 0.0), 2),
                    "tryonRate": self._rate(current_tryons.get(tag, 0.0), clicks),
                    "clickGrowthRate": self._growth(clicks, previous_clicks.get(tag, 0.0)),
                }
            )
        return sorted(
            result,
            key=lambda item: (item["clickGrowthRate"], item["tryonRate"], item["clickCount"]),
            reverse=True,
        )[:12]

    def _event_trend(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for record in records:
            created_at = parse_datetime(str(record.get("createdAt") or ""))
            label = created_at.date().isoformat() if created_at else "unknown"
            buckets[label]["clickCount"] += metric(record, "clickCount")
            buckets[label]["tryonCount"] += metric(record, "tryonCount")
            buckets[label]["conversionCount"] += metric(record, "conversionCount")
        return [
            {"date": date, **{key: round(value, 2) for key, value in values.items()}}
            for date, values in sorted(buckets.items())
        ][-14:]

    def _platform_tag_trends(
        self, current: list[dict[str, Any]], previous: list[dict[str, Any]], field: str
    ) -> list[dict[str, Any]]:
        previous_clicks = self._tag_metric(previous, field, "clickCount")
        current_clicks = self._tag_metric(current, field, "clickCount")
        current_merchants = self._tag_merchants(current, field)
        result = []
        for tag, clicks in current_clicks.items():
            merchant_count = len(current_merchants.get(tag, set()))
            if merchant_count < PLATFORM_MIN_MERCHANTS or clicks < PLATFORM_MIN_EVENTS:
                continue
            result.append(
                {
                    "tag": tag,
                    "clickCount": round(clicks, 2),
                    "merchantCount": merchant_count,
                    "clickGrowthRate": self._growth(clicks, previous_clicks.get(tag, 0.0)),
                }
            )
        return sorted(
            result,
            key=lambda item: (item["clickGrowthRate"], item["clickCount"]),
            reverse=True,
        )[:12]

    def _group_metric(self, records: list[dict[str, Any]], group_key: str, metric_key: str) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for record in records:
            totals[str(record.get(group_key) or "unknown")] += metric(record, metric_key)
        return totals

    def _tag_metric(self, records: list[dict[str, Any]], tag_key: str, metric_key: str) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for record in records:
            tags = record.get(tag_key)
            if not isinstance(tags, list):
                continue
            for tag in tags:
                totals[str(tag)] += metric(record, metric_key)
        return totals

    def _tag_merchants(self, records: list[dict[str, Any]], tag_key: str) -> dict[str, set[str]]:
        merchants: dict[str, set[str]] = defaultdict(set)
        for record in records:
            tags = record.get(tag_key)
            if not isinstance(tags, list):
                continue
            merchant_id = str(record.get("merchantId") or "unknown")
            for tag in tags:
                merchants[str(tag)].add(merchant_id)
        return merchants

    def _rate(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _growth(self, current: float, previous: float) -> float:
        if previous <= 0:
            return 1.0 if current > 0 else 0.0
        return round((current - previous) / previous, 4)


class StrategyAgent:
    def generate(self, dashboard: dict[str, Any], platform: dict[str, Any]) -> list[dict[str, Any]]:
        styles = dashboard.get("stylePerformance", [])
        tags = dashboard.get("tagPerformance", [])
        platform_tags = platform.get("risingTags", [])
        platform_tag_names = {item.get("tag") for item in platform_tags}
        recommendations: list[dict[str, Any]] = []

        if styles:
            best = styles[0]
            matched_tags = [tag for tag in best.get("styleTags", []) if tag in platform_tag_names]
            reasons = [
                f"{best['styleId']} 在当前窗口内点击量为 {best['clickCount']}，试戴率为 {best['tryonRate']:.1%}。",
                f"店内点击增长率为 {best['clickGrowthRate']:.1%}，适合作为短期主推候选。",
            ]
            if matched_tags:
                reasons.append(f"该款式标签 {', '.join(matched_tags)} 与平台匿名上升趋势一致。")
            recommendations.append(
                {
                    "strategyType": "featured_style",
                    "title": "设置试戴页主推款式",
                    "action": {
                        "type": "set_featured_style",
                        "styleId": best["styleId"],
                        "priority": 1,
                        "durationDays": 3,
                    },
                    "reason": reasons,
                    "risk": ["建议先进行 3 天短周期观察，避免样本量较小时过度调整。"],
                    "expectedMetric": {
                        "primary": "tryonRate",
                        "secondary": "favoriteRate",
                    },
                    "confidence": self._confidence(best),
                }
            )

        if tags:
            tag = tags[0]
            recommendations.append(
                {
                    "strategyType": "tag_campaign",
                    "title": f"围绕“{tag['tag']}”组织运营文案",
                    "action": {
                        "type": "promote_tag",
                        "tag": tag["tag"],
                        "durationDays": 5,
                    },
                    "reason": [
                        f"店内“{tag['tag']}”标签点击量为 {tag['clickCount']}，增长率为 {tag['clickGrowthRate']:.1%}。",
                        "可将该标签用于主推款筛选、活动标题和试戴页排序。",
                    ],
                    "risk": ["标签热度需要结合库存、服务时长和客单价人工复核。"],
                    "expectedMetric": {
                        "primary": "clickRate",
                        "secondary": "conversionRate",
                    },
                    "confidence": "medium",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "strategyType": "data_collection",
                    "title": "继续积累运营数据",
                    "action": {
                        "type": "collect_more_events",
                        "durationDays": 7,
                    },
                    "reason": ["当前商家样本不足，暂不建议自动调整主推款式。"],
                    "risk": ["数据不足时生成策略容易波动。"],
                    "expectedMetric": {
                        "primary": "clickCount",
                        "secondary": "tryonCount",
                    },
                    "confidence": "low",
                }
            )
        return recommendations

    def _confidence(self, style: dict[str, Any]) -> str:
        if style.get("clickCount", 0) >= 30 and style.get("tryonRate", 0) >= 0.2:
            return "high"
        if style.get("clickCount", 0) >= 10:
            return "medium"
        return "low"


class SafetyReviewAgent:
    def review(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        reviewed = []
        blocked_words = ["其他商家", "附近商家", "竞品店", "merchant_"]
        for recommendation in recommendations:
            safe = json.loads(json.dumps(recommendation, ensure_ascii=False))
            text = json.dumps(safe, ensure_ascii=False)
            safe["safety"] = {
                "passed": not any(word in text for word in blocked_words),
                "policy": "No other merchant raw data or merchant identifiers may be exposed.",
            }
            reviewed.append(safe)
        return reviewed


class OpenClawStrategyAdapter:
    """OpenClaw adapter for personalized, explainable strategy assistance.

    The local rule engine remains the source of truth for ranking and safety.
    OpenClaw is used as the assistant gateway for natural-language explanation,
    merchant-specific preference handling, and multi-channel handoff.
    """

    def __init__(self) -> None:
        self.webhook_url = os.getenv("OPENCLAW_STRATEGY_WEBHOOK_URL", "").strip()
        self.channel = os.getenv("OPENCLAW_STRATEGY_CHANNEL", "merchant-dashboard").strip()
        self.timeout_seconds = float(os.getenv("OPENCLAW_STRATEGY_TIMEOUT", "4"))

    def status(self) -> dict[str, Any]:
        configured = bool(self.webhook_url)
        return {
            "enabled": configured,
            "provider": "OpenClaw",
            "channel": self.channel,
            "mode": "gateway" if configured else "local-explainable-fallback",
            "message": (
                "OpenClaw strategy gateway is configured."
                if configured
                else "OpenClaw webhook is not configured; using local explainable strategy assistant."
            ),
        }

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        local_payload = self._local_explanation(context)
        if not self.webhook_url:
            return local_payload

        request_payload = {
            "task": "merchant_strategy_assistant",
            "channel": self.channel,
            "merchantId": context.get("merchantId"),
            "windowDays": context.get("windowDays"),
            "rulesOutput": context.get("recommendations", []),
            "dashboard": self._compact_dashboard(context.get("dashboard", {})),
            "platformTrends": self._compact_platform(context.get("platformTrends", {})),
            "requirements": {
                "explainability": True,
                "respectRuleRanking": True,
                "noCrossMerchantRawData": True,
                "outputSchema": [
                    "summary",
                    "recommendations[].assistantExplanation",
                    "recommendations[].merchantPersonalization",
                    "handoff",
                ],
            },
        }
        try:
            response = self._post_json(request_payload)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            local_payload["ai"]["enabled"] = False
            local_payload["ai"]["mode"] = "openclaw-fallback"
            local_payload["ai"]["message"] = f"OpenClaw call failed; local explanation used: {exc}"
            return local_payload

        return self._merge_openclaw_response(context, local_payload, response)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("OpenClaw response must be a JSON object")
        return parsed

    def _merge_openclaw_response(
        self,
        context: dict[str, Any],
        local_payload: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        recommendations = json.loads(json.dumps(local_payload["recommendations"], ensure_ascii=False))
        openclaw_items = response.get("recommendations")
        if isinstance(openclaw_items, list):
            by_type = {
                str(item.get("strategyType") or item.get("type") or ""): item
                for item in openclaw_items
                if isinstance(item, dict)
            }
            for item in recommendations:
                match = by_type.get(str(item.get("strategyType") or ""))
                if not match:
                    continue
                if isinstance(match.get("assistantExplanation"), str):
                    item["assistantExplanation"] = match["assistantExplanation"]
                if isinstance(match.get("merchantPersonalization"), dict):
                    item["merchantPersonalization"] = match["merchantPersonalization"]

        return {
            **local_payload,
            "summary": str(response.get("summary") or local_payload["summary"]),
            "recommendations": recommendations,
            "ai": {
                **self.status(),
                "enabled": True,
                "mode": "openclaw-gateway",
            },
            "handoff": {
                **local_payload["handoff"],
                "openclaw": True,
                "source": response.get("source") or "OpenClaw",
            },
            "rawOpenClaw": response if os.getenv("OPENCLAW_DEBUG_RESPONSE") == "1" else None,
        }

    def _local_explanation(self, context: dict[str, Any]) -> dict[str, Any]:
        recommendations = json.loads(json.dumps(context.get("recommendations", []), ensure_ascii=False))
        dashboard = context.get("dashboard", {})
        platform = context.get("platformTrends", {})
        summary = dashboard.get("summary", {})
        for item in recommendations:
            item["assistantExplanation"] = self._explain_recommendation(item, summary, platform)
            item["merchantPersonalization"] = self._personalization(item, dashboard)
            item["explainability"] = {
                "source": "rules + OpenClaw-ready local explanation",
                "decisionInputs": self._decision_inputs(item),
                "guardrails": [
                    "Only this merchant's own raw metrics are used.",
                    "Platform signals are aggregated behind privacy thresholds.",
                    "Recommendations keep a short observation window before automation.",
                ],
            }

        return {
            "summary": self._assistant_summary(context, recommendations),
            "recommendations": recommendations,
            "ai": self.status(),
            "handoff": {
                "openclaw": bool(self.webhook_url),
                "channel": self.channel,
                "merchantId": context.get("merchantId"),
                "intents": [
                    "explain_strategy",
                    "personalize_campaign",
                    "follow_up_from_external_channel",
                ],
            },
        }

    def _assistant_summary(self, context: dict[str, Any], recommendations: list[dict[str, Any]]) -> str:
        merchant_id = context.get("merchantId")
        window_days = context.get("windowDays")
        count = len(recommendations)
        return f"OpenClaw strategy assistant prepared {count} explainable recommendation(s) for {merchant_id} over {window_days} day(s)."

    def _explain_recommendation(
        self,
        item: dict[str, Any],
        summary: dict[str, Any],
        platform: dict[str, Any],
    ) -> str:
        primary_metric = item.get("expectedMetric", {}).get("primary", "clickRate")
        platform_count = len(platform.get("risingTags", []) or [])
        return (
            f"This suggestion is ranked by the local rules, then explained for the merchant: "
            f"the primary metric to watch is {primary_metric}, current click growth is "
            f"{summary.get('clickGrowthRate', 0):.1%}, and {platform_count} privacy-safe platform trend(s) "
            "are available for context."
        )

    def _personalization(self, item: dict[str, Any], dashboard: dict[str, Any]) -> dict[str, Any]:
        action = item.get("action", {})
        top_tags = [tag.get("tag") for tag in dashboard.get("tagPerformance", [])[:3] if isinstance(tag, dict)]
        return {
            "merchantTone": "data-backed and cautious",
            "suggestedPrompt": self._suggested_prompt(action, top_tags),
            "followUpQuestion": "Should I turn this into a campaign copy, a featured-style action, or a 3-day observation plan?",
        }

    def _suggested_prompt(self, action: dict[str, Any], top_tags: list[str]) -> str:
        if action.get("type") == "promote_tag":
            return f"Create a campaign plan around {action.get('tag')} for my store."
        if action.get("type") == "set_featured_style":
            return f"Explain why {action.get('styleId')} should be featured and what risk I should watch."
        tags = ", ".join(tag for tag in top_tags if tag)
        return f"Review my store performance and suggest the next action. Top tags: {tags}."

    def _decision_inputs(self, item: dict[str, Any]) -> list[str]:
        inputs = ["strategyType", "confidence", "expectedMetric"]
        action = item.get("action", {})
        if action.get("styleId"):
            inputs.append("styleId")
        if action.get("tag"):
            inputs.append("tag")
        return inputs

    def _compact_dashboard(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        return {
            "merchantId": dashboard.get("merchantId"),
            "windowDays": dashboard.get("windowDays"),
            "summary": dashboard.get("summary"),
            "topStyles": (dashboard.get("stylePerformance") or [])[:5],
            "topTags": (dashboard.get("tagPerformance") or [])[:5],
        }

    def _compact_platform(self, platform: dict[str, Any]) -> dict[str, Any]:
        return {
            "privacy": platform.get("privacy"),
            "risingTags": (platform.get("risingTags") or [])[:5],
            "risingScenarios": (platform.get("risingScenarios") or [])[:5],
        }


AiStrategyAdapter = OpenClawStrategyAdapter
