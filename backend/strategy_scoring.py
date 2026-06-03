from __future__ import annotations

from typing import Any

from strategy_schema import StrategySignal


class StrategyScoringEngine:
    """Ranks strategy signals while keeping the current production behavior stable."""

    def style_sort_key(self, style: dict[str, Any]) -> tuple[float, float, float]:
        return self.signal_sort_key(StrategySignal.from_style(style))

    def tag_sort_key(self, tag: dict[str, Any]) -> tuple[float, float, float]:
        return self.signal_sort_key(StrategySignal.from_tag(tag))

    def signal_sort_key(self, signal: StrategySignal) -> tuple[float, float, float]:
        return (
            signal.clickGrowthRate,
            signal.tryonRate,
            signal.clickCount,
        )

    def rank_styles(self, styles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(styles, key=self.style_sort_key, reverse=True)

    def rank_tags(self, tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(tags, key=self.tag_sort_key, reverse=True)

    def confidence(self, signal: StrategySignal) -> str:
        if signal.clickCount >= 30 and signal.tryonRate >= 0.2:
            return "high"
        if signal.clickCount >= 10:
            return "medium"
        return "low"
