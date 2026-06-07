from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MERCHANT_OPS_LOG = ROOT / "backend" / "data" / "merchant_ops_test_records.jsonl"
MERCHANT_STYLE_TAGS = ROOT / "backend" / "data" / "merchant_style_tags.json"


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


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


class MerchantOpsStore:
    def __init__(self, path: Path = MERCHANT_OPS_LOG) -> None:
        self.path = path

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = self._normalize(payload)
        append_jsonl(self.path, [record])
        return record

    def append_many(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = [self._normalize(payload) for payload in payloads]
        append_jsonl(self.path, records)
        return records

    def list_records(self, limit: int = 200) -> list[dict[str, Any]]:
        valid_records = [record for record in read_jsonl(self.path) if not record.get("_invalid")]
        if limit <= 0:
            return valid_records
        return valid_records[-limit:]

    def summary(self) -> dict[str, Any]:
        records = self.list_records(limit=0)
        merchant_counts = Counter(str(record.get("merchantId") or "unknown") for record in records)
        style_counts = Counter(str(record.get("styleId") or "unknown") for record in records)
        event_counts = Counter(str(record.get("eventType") or "unknown") for record in records)
        scenario_counts = Counter(
            tag
            for record in records
            for tag in record.get("scenarioTags", [])
            if isinstance(tag, str) and tag
        )

        return {
            "ok": True,
            "store": str(self.path.relative_to(ROOT)),
            "recordCount": len(records),
            "merchantCount": len(merchant_counts),
            "eventTypes": event_counts.most_common(),
            "topStyles": style_counts.most_common(20),
            "topMerchants": merchant_counts.most_common(20),
            "scenarioTags": scenario_counts.most_common(20),
            "updatedAt": utc_now(),
        }

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        created_at = str(payload.get("createdAt") or utc_now())
        record = {
            "recordId": str(payload.get("recordId") or self._record_id(payload, created_at)),
            "createdAt": created_at,
            "merchantId": str(payload.get("merchantId") or "demo_merchant"),
            "eventType": str(payload.get("eventType") or "merchant_ops_sample"),
            "styleId": str(payload.get("styleId") or ""),
            "sessionId": str(payload.get("sessionId") or ""),
            "userSegment": str(payload.get("userSegment") or ""),
            "scenarioTags": self._string_list(payload.get("scenarioTags")),
            "styleTags": self._string_list(payload.get("styleTags")),
            "metrics": payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {},
            "notes": str(payload.get("notes") or ""),
            "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
        }
        return record

    def _record_id(self, payload: dict[str, Any], created_at: str) -> str:
        stable = json.dumps(payload, ensure_ascii=False, sort_keys=True) + created_at
        digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]
        return f"merchant_ops_{digest}"

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]


class MerchantStyleTagStore:
    """Persist user-facing style labels chosen from merchant operations."""

    def __init__(self, path: Path = MERCHANT_STYLE_TAGS) -> None:
        self.path = path

    def list_tags(self, merchant_id: str = "merchant_001") -> dict[str, Any]:
        data = self._read()
        merchant = data.get(merchant_id) if isinstance(data.get(merchant_id), dict) else {}
        styles = merchant.get("styles") if isinstance(merchant.get("styles"), dict) else {}
        return {
            "ok": True,
            "merchantId": merchant_id,
            "styles": styles,
            "updatedAt": merchant.get("updatedAt") or "",
        }

    def upsert_style_tags(self, merchant_id: str, style_id: str, tags: dict[str, Any]) -> dict[str, Any]:
        safe_merchant_id = str(merchant_id or "merchant_001")
        safe_style_id = str(style_id or "").strip()
        if not safe_style_id:
            raise ValueError("styleId is required")

        data = self._read()
        merchant = data.setdefault(safe_merchant_id, {"styles": {}})
        if not isinstance(merchant, dict):
            merchant = {"styles": {}}
            data[safe_merchant_id] = merchant
        styles = merchant.setdefault("styles", {})
        if not isinstance(styles, dict):
            styles = {}
            merchant["styles"] = styles

        current = styles.get(safe_style_id) if isinstance(styles.get(safe_style_id), dict) else {}
        normalized = self._normalize_tags(tags, current)
        styles[safe_style_id] = normalized
        merchant["updatedAt"] = utc_now()
        self._write(data)
        return {
            "ok": True,
            "merchantId": safe_merchant_id,
            "styleId": safe_style_id,
            "tags": normalized,
            "styles": styles,
            "updatedAt": merchant["updatedAt"],
        }

    def _normalize_tags(self, tags: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        result = dict(current)
        if "featuredLabel" in tags:
            result["featuredLabel"] = str(tags.get("featuredLabel") or "").strip()
        if "promotionLabel" in tags:
            result["promotionLabel"] = str(tags.get("promotionLabel") or "").strip()
        if "promotionOffer" in tags:
            result["promotionOffer"] = str(tags.get("promotionOffer") or "").strip()
        if "promotionStrategy" in tags and isinstance(tags.get("promotionStrategy"), dict):
            result["promotionStrategy"] = tags["promotionStrategy"]
        result["updatedAt"] = utc_now()
        return {key: value for key, value in result.items() if value not in {"", None}}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                parsed = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
