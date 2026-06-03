from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


STRATEGY_SCHEMA_VERSION = "strategy-recommendation-v1"
StrategyType = Literal["featured_style", "tag_campaign", "data_collection"]
Confidence = Literal["low", "medium", "high"]
SignalKind = Literal["style", "tag"]


@dataclass(frozen=True)
class StrategySignal:
    kind: SignalKind
    entityId: str
    clickCount: float
    tryonRate: float
    clickGrowthRate: float
    conversionRate: float = 0.0
    favoriteRate: float = 0.0
    platformTrendMatched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "entityId": self.entityId,
            "clickCount": self.clickCount,
            "tryonRate": self.tryonRate,
            "clickGrowthRate": self.clickGrowthRate,
            "conversionRate": self.conversionRate,
            "favoriteRate": self.favoriteRate,
            "platformTrendMatched": self.platformTrendMatched,
        }

    @classmethod
    def from_style(cls, style: dict[str, Any], platform_trend_matched: bool = False) -> "StrategySignal":
        return cls(
            kind="style",
            entityId=str(style.get("styleId") or "unknown"),
            clickCount=_safe_float(style.get("clickCount")),
            tryonRate=_safe_float(style.get("tryonRate")),
            clickGrowthRate=_safe_float(style.get("clickGrowthRate")),
            conversionRate=_safe_float(style.get("conversionRate")),
            favoriteRate=_safe_float(style.get("favoriteRate")),
            platformTrendMatched=platform_trend_matched,
        )

    @classmethod
    def from_tag(cls, tag: dict[str, Any], platform_trend_matched: bool = False) -> "StrategySignal":
        return cls(
            kind="tag",
            entityId=str(tag.get("tag") or "unknown"),
            clickCount=_safe_float(tag.get("clickCount")),
            tryonRate=_safe_float(tag.get("tryonRate")),
            clickGrowthRate=_safe_float(tag.get("clickGrowthRate")),
            platformTrendMatched=platform_trend_matched,
        )


@dataclass(frozen=True)
class StrategyAction:
    type: str
    durationDays: int
    styleId: str | None = None
    tag: str | None = None
    priority: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "durationDays": self.durationDays,
        }
        if self.styleId:
            result["styleId"] = self.styleId
        if self.tag:
            result["tag"] = self.tag
        if self.priority is not None:
            result["priority"] = self.priority
        return result


@dataclass(frozen=True)
class ExpectedMetric:
    primary: str
    secondary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
        }


@dataclass(frozen=True)
class StrategyRecommendation:
    strategyType: StrategyType
    title: str
    action: StrategyAction
    reason: list[str]
    risk: list[str]
    expectedMetric: ExpectedMetric
    confidence: Confidence
    schemaVersion: str = STRATEGY_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": self.schemaVersion,
            "strategyType": self.strategyType,
            "title": self.title,
            "action": self.action.to_dict(),
            "reason": self.reason,
            "risk": self.risk,
            "expectedMetric": self.expectedMetric.to_dict(),
            "confidence": self.confidence,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


def normalize_strategy_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
    """Return a stable recommendation shape while preserving enrichment fields."""
    normalized = dict(recommendation)
    normalized["schemaVersion"] = str(normalized.get("schemaVersion") or STRATEGY_SCHEMA_VERSION)
    normalized["strategyType"] = str(normalized.get("strategyType") or "data_collection")
    normalized["title"] = str(normalized.get("title") or "运营策略建议")

    action = normalized.get("action") if isinstance(normalized.get("action"), dict) else {}
    normalized["action"] = {
        "type": str(action.get("type") or "collect_more_events"),
        "durationDays": _safe_positive_int(action.get("durationDays"), default=7),
    }
    for optional_key in ("styleId", "tag", "priority"):
        if optional_key in action:
            normalized["action"][optional_key] = action[optional_key]

    normalized["reason"] = _string_list(normalized.get("reason"))
    normalized["risk"] = _string_list(normalized.get("risk"))

    expected = normalized.get("expectedMetric") if isinstance(normalized.get("expectedMetric"), dict) else {}
    normalized["expectedMetric"] = {
        "primary": str(expected.get("primary") or "clickRate"),
        "secondary": str(expected.get("secondary") or "tryonRate"),
    }

    confidence = str(normalized.get("confidence") or "low")
    normalized["confidence"] = confidence if confidence in {"low", "medium", "high"} else "low"
    return normalized


def validate_strategy_recommendation(recommendation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if recommendation.get("schemaVersion") != STRATEGY_SCHEMA_VERSION:
        errors.append("schemaVersion must be strategy-recommendation-v1")
    if recommendation.get("strategyType") not in {"featured_style", "tag_campaign", "data_collection"}:
        errors.append("strategyType is unsupported")
    if not isinstance(recommendation.get("title"), str) or not recommendation["title"].strip():
        errors.append("title is required")
    if not isinstance(recommendation.get("action"), dict):
        errors.append("action must be an object")
    if not recommendation.get("reason"):
        errors.append("reason must contain at least one item")
    if recommendation.get("confidence") not in {"low", "medium", "high"}:
        errors.append("confidence must be low, medium, or high")
    expected = recommendation.get("expectedMetric")
    if not isinstance(expected, dict) or not expected.get("primary") or not expected.get("secondary"):
        errors.append("expectedMetric.primary and expectedMetric.secondary are required")
    return errors


def _safe_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def _safe_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
