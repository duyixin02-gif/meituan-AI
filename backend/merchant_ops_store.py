from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MERCHANT_OPS_LOG = ROOT / "backend" / "data" / "merchant_ops_test_records.jsonl"


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
