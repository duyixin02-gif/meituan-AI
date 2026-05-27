from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG = ROOT / "backend" / "data" / "click_events.jsonl"
FEATURE_LOG = ROOT / "backend" / "data" / "structured_click_features.jsonl"
SUMMARY_STORE = ROOT / "backend" / "data" / "structured_click_summary.json"

STYLE_CLICK_EVENTS = {
    "style_click",
    "local_preview_generated",
    "ai_tryon_completed",
    "ai_tryon_failed",
}


@dataclass(frozen=True)
class CleanClickEvent:
    event_id: str
    event_type: str
    session_id: str
    style_id: str
    pair_id: str
    page: str
    client_ip: str
    occurred_at: str
    received_at: str
    title: str
    source_paths: dict[str, str]
    source_urls: dict[str, str]


@dataclass(frozen=True)
class NaturalLanguageFeatureRecord:
    record_id: str
    source_event_id: str
    session_id: str
    style_id: str
    event_type: str
    generated_at: str
    behavior_text: str
    visual_basic_tags: list[str]
    nail_shape_structure_tags: list[str]
    user_scene_crowd_tags: list[str]
    analysis_notes: list[str]
    source: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append(
                    {
                        "_invalid": True,
                        "_lineNumber": line_number,
                        "_raw": line,
                    }
                )
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


class JsonlEventRepository:
    def __init__(self, event_log: Path = EVENT_LOG) -> None:
        self.event_log = event_log

    def list_events(self) -> list[dict[str, Any]]:
        return read_jsonl(self.event_log)


class ClickEventCleanerAgent:
    def clean(self, raw_events: list[dict[str, Any]]) -> list[CleanClickEvent]:
        cleaned: list[CleanClickEvent] = []
        for index, event in enumerate(raw_events, start=1):
            if event.get("_invalid"):
                continue

            event_type = str(event.get("eventType") or "").strip()
            if event_type not in STYLE_CLICK_EVENTS:
                continue

            detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
            style_id = str(detail.get("styleId") or event.get("styleId") or "").strip()
            if not style_id:
                continue

            received_at = str(event.get("receivedAt") or "")
            occurred_at = str(event.get("createdAt") or received_at or utc_now())
            event_id = self._build_event_id(event, index)
            cleaned.append(
                CleanClickEvent(
                    event_id=event_id,
                    event_type=event_type,
                    session_id=str(event.get("sessionId") or "anonymous"),
                    style_id=style_id,
                    pair_id=str(detail.get("pairId") or ""),
                    page=str(event.get("page") or ""),
                    client_ip=str(event.get("clientIp") or ""),
                    occurred_at=occurred_at,
                    received_at=received_at,
                    title=str(detail.get("title") or style_id),
                    source_paths={
                        "hand": str(detail.get("handPath") or ""),
                        "style_original": str(detail.get("styleOriginalPath") or ""),
                        "style_enhanced": str(detail.get("styleEnhancedPath") or ""),
                        "style_preview": str(detail.get("stylePreviewPath") or ""),
                    },
                    source_urls={
                        "hand": str(detail.get("handSourceUrl") or ""),
                        "style_original": str(detail.get("styleOriginalUrl") or ""),
                        "style_enhanced": str(detail.get("styleEnhancedUrl") or ""),
                    },
                )
            )
        return cleaned

    def _build_event_id(self, event: dict[str, Any], index: int) -> str:
        session_id = str(event.get("sessionId") or "anonymous")
        event_type = str(event.get("eventType") or "event")
        created_at = str(event.get("createdAt") or event.get("receivedAt") or index)
        stable = f"{session_id}|{event_type}|{created_at}|{index}"
        digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]
        return f"evt_{digest}"


class StyleFeatureAgent:
    def describe(self, event: CleanClickEvent) -> NaturalLanguageFeatureRecord:
        visual_tags = self._visual_basic_tags(event)
        structure_tags = self._structure_tags(event)
        scene_tags = self._scene_crowd_tags(event)
        behavior_text = self._behavior_text(event, visual_tags, structure_tags, scene_tags)

        return NaturalLanguageFeatureRecord(
            record_id=f"feature_{event.event_id}",
            source_event_id=event.event_id,
            session_id=event.session_id,
            style_id=event.style_id,
            event_type=event.event_type,
            generated_at=utc_now(),
            behavior_text=behavior_text,
            visual_basic_tags=visual_tags,
            nail_shape_structure_tags=structure_tags,
            user_scene_crowd_tags=scene_tags,
            analysis_notes=[
                "当前版本基于点击事件、款式图片路径和事件类型生成自然语言标签。",
                "视觉细节可在后续接入多模态模型后替换为真实图像理解结果。",
            ],
            source={
                "title": event.title,
                "pairId": event.pair_id,
                "page": event.page,
                "sourcePaths": event.source_paths,
                "sourceUrls": event.source_urls,
            },
        )

    def _visual_basic_tags(self, event: CleanClickEvent) -> list[str]:
        tags = ["美甲款式图", "用户主动查看", "可试戴款"]
        if event.source_paths.get("style_enhanced") or event.source_urls.get("style_enhanced"):
            tags.append("存在增强预览图")
        if event.source_paths.get("style_original") or event.source_urls.get("style_original"):
            tags.append("存在原始款式图")
        if event.event_type == "ai_tryon_completed":
            tags.append("已生成AI试戴效果")
        elif event.event_type == "local_preview_generated":
            tags.append("已生成本地试戴预览")
        return tags

    def _structure_tags(self, event: CleanClickEvent) -> list[str]:
        tags = ["甲型待视觉识别", "结构细节待补充", "适合进入款式结构标注队列"]
        if event.source_paths.get("hand"):
            tags.append("有关联手部样例图")
        if event.event_type in {"local_preview_generated", "ai_tryon_completed"}:
            tags.append("已发生试戴结构匹配行为")
        return tags

    def _scene_crowd_tags(self, event: CleanClickEvent) -> list[str]:
        tags = ["试戴意向用户", "款式探索场景"]
        if event.event_type == "style_click":
            tags.append("浏览比较阶段")
        if event.event_type == "local_preview_generated":
            tags.append("低成本预览阶段")
        if event.event_type == "ai_tryon_completed":
            tags.append("高意向试戴阶段")
        if event.event_type == "ai_tryon_failed":
            tags.append("试戴受阻用户")
        return tags

    def _behavior_text(
        self,
        event: CleanClickEvent,
        visual_tags: list[str],
        structure_tags: list[str],
        scene_tags: list[str],
    ) -> str:
        action = {
            "style_click": "点击查看了款式",
            "local_preview_generated": "触发了本地试戴预览",
            "ai_tryon_completed": "完成了一次AI试戴",
            "ai_tryon_failed": "尝试AI试戴但未成功",
        }.get(event.event_type, "产生了款式相关行为")
        return (
            f"用户会话 {event.session_id} 在 {event.occurred_at} {action} {event.title}"
            f"（{event.style_id}）。该行为可自然语言归档为：视觉基础标签包含"
            f"{'、'.join(visual_tags)}；甲型与结构标签包含{'、'.join(structure_tags)}；"
            f"用户侧场景与人群标签包含{'、'.join(scene_tags)}。"
        )


class FeatureStore:
    def __init__(self, feature_log: Path = FEATURE_LOG, summary_store: Path = SUMMARY_STORE) -> None:
        self.feature_log = feature_log
        self.summary_store = summary_store

    def existing_record_ids(self) -> set[str]:
        return {
            str(record.get("record_id"))
            for record in read_jsonl(self.feature_log)
            if record.get("record_id")
        }

    def append_new(self, records: list[NaturalLanguageFeatureRecord]) -> int:
        existing_ids = self.existing_record_ids()
        new_records = [asdict(record) for record in records if record.record_id not in existing_ids]
        return append_jsonl(self.feature_log, new_records)

    def save_summary(self, summary: dict[str, Any]) -> None:
        write_json(self.summary_store, summary)

    def load_summary(self) -> dict[str, Any]:
        if self.summary_store.exists():
            return json.loads(self.summary_store.read_text(encoding="utf-8"))
        return {}


class DataAgentOrchestrator:
    def __init__(
        self,
        repository: JsonlEventRepository | None = None,
        cleaner: ClickEventCleanerAgent | None = None,
        feature_agent: StyleFeatureAgent | None = None,
        store: FeatureStore | None = None,
    ) -> None:
        self.repository = repository or JsonlEventRepository()
        self.cleaner = cleaner or ClickEventCleanerAgent()
        self.feature_agent = feature_agent or StyleFeatureAgent()
        self.store = store or FeatureStore()

    def run(self) -> dict[str, Any]:
        raw_events = self.repository.list_events()
        clean_events = self.cleaner.clean(raw_events)
        feature_records = [self.feature_agent.describe(event) for event in clean_events]
        appended = self.store.append_new(feature_records)
        summary = self._summarize(raw_events, clean_events, feature_records, appended)
        self.store.save_summary(summary)
        return summary

    def latest_summary(self) -> dict[str, Any]:
        summary = self.store.load_summary()
        if summary:
            return summary
        return self.run()

    def _summarize(
        self,
        raw_events: list[dict[str, Any]],
        clean_events: list[CleanClickEvent],
        feature_records: list[NaturalLanguageFeatureRecord],
        appended: int,
    ) -> dict[str, Any]:
        event_type_counts = Counter(event.event_type for event in clean_events)
        style_counts = Counter(event.style_id for event in clean_events)
        session_counts = Counter(event.session_id for event in clean_events)
        tag_counts: dict[str, Counter[str]] = {
            "visualBasic": Counter(),
            "nailShapeStructure": Counter(),
            "userSceneCrowd": Counter(),
        }
        style_profiles: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "clickCount": 0,
                "behaviorTexts": [],
                "visualBasicTags": Counter(),
                "nailShapeStructureTags": Counter(),
                "userSceneCrowdTags": Counter(),
            }
        )

        for record in feature_records:
            tag_counts["visualBasic"].update(record.visual_basic_tags)
            tag_counts["nailShapeStructure"].update(record.nail_shape_structure_tags)
            tag_counts["userSceneCrowd"].update(record.user_scene_crowd_tags)

            profile = style_profiles[record.style_id]
            profile["clickCount"] += 1
            profile["behaviorTexts"].append(record.behavior_text)
            profile["visualBasicTags"].update(record.visual_basic_tags)
            profile["nailShapeStructureTags"].update(record.nail_shape_structure_tags)
            profile["userSceneCrowdTags"].update(record.user_scene_crowd_tags)

        return {
            "ok": True,
            "generatedAt": utc_now(),
            "input": {
                "rawEventCount": len(raw_events),
                "cleanStyleEventCount": len(clean_events),
            },
            "output": {
                "featureLog": str(FEATURE_LOG.relative_to(ROOT)),
                "summaryStore": str(SUMMARY_STORE.relative_to(ROOT)),
                "newFeatureRecords": appended,
                "totalFeatureCandidates": len(feature_records),
            },
            "stats": {
                "eventTypes": dict(event_type_counts),
                "topStyles": style_counts.most_common(10),
                "sessionCount": len(session_counts),
                "tagCounts": {
                    key: counter.most_common(20) for key, counter in tag_counts.items()
                },
            },
            "styleProfiles": {
                style_id: {
                    "clickCount": profile["clickCount"],
                    "sampleBehaviorText": profile["behaviorTexts"][0]
                    if profile["behaviorTexts"]
                    else "",
                    "visualBasicTags": [tag for tag, _ in profile["visualBasicTags"].most_common()],
                    "nailShapeStructureTags": [
                        tag for tag, _ in profile["nailShapeStructureTags"].most_common()
                    ],
                    "userSceneCrowdTags": [
                        tag for tag, _ in profile["userSceneCrowdTags"].most_common()
                    ],
                }
                for style_id, profile in sorted(style_profiles.items())
            },
        }
