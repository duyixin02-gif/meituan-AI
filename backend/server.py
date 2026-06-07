from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from assistant_gateway import OfficeAssistantGateway
from data_agent import DataAgentOrchestrator
from demo_data import seed_demo_records
from merchant_ops_store import MerchantOpsStore, MerchantStyleTagStore
from ops_agent import OpsAnalyticsService
from seedream_client import SeedreamConfigError, SeedreamRequestError
from tryon_service import TryonService


ROOT = Path(__file__).resolve().parents[1]
EVENT_LOG = ROOT / "backend" / "data" / "click_events.jsonl"


def write_json(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            write_json(
                self,
                200,
                {
                    "ok": True,
                    "service": "meituan-nail-tryon-backend",
                    "endpoints": [
                        "/api/events",
                        "/api/tryon",
                        "/api/data-agent/run",
                        "/api/data-agent/summary",
                        "/api/merchant-ops/records",
                        "/api/merchant-ops/summary",
                        "/api/ops/merchant-dashboard",
                        "/api/ops/platform-trends",
                        "/api/ops/strategy/run",
                        "/api/ops/strategy/explain",
                        "/api/ops/strategy/accept",
                        "/api/ops/campaign/generate",
                        "/api/ops/style-tags",
                        "/api/assistant/message",
                        "/api/assistant/capabilities",
                        "/api/ops/demo-data",
                    ],
                },
            )
            return
        if parsed.path == "/api/assistant/capabilities":
            write_json(self, 200, OfficeAssistantGateway().capabilities())
            return
        if parsed.path == "/api/data-agent/summary":
            write_json(self, 200, DataAgentOrchestrator().latest_summary())
            return
        if parsed.path == "/api/merchant-ops/records":
            query = parse_query(parsed.query)
            limit = parse_int(query.get("limit"), default=200)
            write_json(
                self,
                200,
                {
                    "ok": True,
                    "records": MerchantOpsStore().list_records(limit=limit),
                },
            )
            return
        if parsed.path == "/api/merchant-ops/summary":
            write_json(self, 200, MerchantOpsStore().summary())
            return
        if parsed.path == "/api/ops/merchant-dashboard":
            query = parse_query(parsed.query)
            merchant_id = query.get("merchantId", "merchant_001")
            window_days = parse_int(query.get("windowDays"), default=7)
            write_json(
                self,
                200,
                OpsAnalyticsService().merchant_dashboard(merchant_id, window_days),
            )
            return
        if parsed.path == "/api/ops/platform-trends":
            query = parse_query(parsed.query)
            window_days = parse_int(query.get("windowDays"), default=7)
            write_json(self, 200, OpsAnalyticsService().platform_trends(window_days))
            return
        if parsed.path == "/api/ops/style-tags":
            query = parse_query(parsed.query)
            merchant_id = query.get("merchantId", "merchant_001")
            write_json(self, 200, MerchantStyleTagStore().list_tags(merchant_id))
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {
            "/api/events",
            "/api/tryon",
            "/api/data-agent/run",
            "/api/merchant-ops/records",
            "/api/ops/strategy/run",
            "/api/ops/strategy/explain",
            "/api/ops/strategy/accept",
            "/api/ops/campaign/generate",
            "/api/ops/style-tags",
            "/api/assistant/message",
            "/api/ops/demo-data",
        }:
            self.send_error(404, "Unknown endpoint")
            return

        if parsed.path == "/api/data-agent/run":
            write_json(self, 200, DataAgentOrchestrator().run())
            return

        if parsed.path == "/api/ops/demo-data":
            write_json(self, 200, seed_demo_records())
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if parsed.path == "/api/merchant-ops/records":
            self.handle_merchant_ops_records(payload)
            return

        if parsed.path == "/api/ops/strategy/run":
            merchant_id = str(payload.get("merchantId") or "merchant_001")
            window_days = parse_int(str(payload.get("windowDays")) if payload.get("windowDays") else None, 7)
            write_json(self, 200, OpsAnalyticsService().generate_strategy(merchant_id, window_days))
            return

        if parsed.path == "/api/assistant/message":
            write_json(self, 200, OfficeAssistantGateway().handle_message(payload))
            return

        if parsed.path == "/api/ops/strategy/explain":
            payload["intent"] = "explain_strategy"
            write_json(self, 200, OfficeAssistantGateway().handle_message(payload))
            return

        if parsed.path == "/api/ops/campaign/generate":
            payload["intent"] = "generate_campaign"
            write_json(self, 200, OfficeAssistantGateway().handle_message(payload))
            return

        if parsed.path == "/api/ops/style-tags":
            try:
                result = MerchantStyleTagStore().upsert_style_tags(
                    str(payload.get("merchantId") or "merchant_001"),
                    str(payload.get("styleId") or ""),
                    payload.get("tags") if isinstance(payload.get("tags"), dict) else payload,
                )
            except ValueError as exc:
                write_json(self, 400, {"ok": False, "message": str(exc)})
            else:
                write_json(self, 200, result)
            return

        if parsed.path == "/api/ops/strategy/accept":
            payload["intent"] = "accept_strategy"
            write_json(self, 200, OfficeAssistantGateway().handle_message(payload))
            return

        if parsed.path == "/api/tryon":
            self.handle_tryon(payload)
            return

        event = {
            "receivedAt": datetime.now(timezone.utc).isoformat(),
            "clientIp": self.client_address[0],
            **payload,
        }
        EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with EVENT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        write_json(self, 200, {"ok": True, "stored": str(EVENT_LOG.relative_to(ROOT))})

    def handle_tryon(self, payload: dict) -> None:
        try:
            result = TryonService().create_tryon(payload)
        except SeedreamConfigError as exc:
            write_json(
                self,
                503,
                {
                    "ok": False,
                    "errorCode": "seedream_not_configured",
                    "message": str(exc),
                },
            )
        except SeedreamRequestError as exc:
            write_json(
                self,
                502,
                {
                    "ok": False,
                    "errorCode": "seedream_request_failed",
                    "message": str(exc),
                },
            )
        except (ValueError, FileNotFoundError) as exc:
            write_json(
                self,
                400,
                {
                    "ok": False,
                    "errorCode": "invalid_tryon_request",
                    "message": str(exc),
                },
            )
        else:
            write_json(self, 200, result)

    def handle_merchant_ops_records(self, payload: dict) -> None:
        store = MerchantOpsStore()
        records_payload = payload.get("records")
        if isinstance(records_payload, list):
            records = [
                item for item in records_payload if isinstance(item, dict)
            ]
            stored = store.append_many(records)
        else:
            stored = [store.append(payload)]

        write_json(
            self,
            200,
            {
                "ok": True,
                "storedCount": len(stored),
                "records": stored,
                "summary": store.summary(),
            },
        )


def main() -> int:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Serving on http://{host}:{port}/frontend/index.html")
    print(f"Event log: {EVENT_LOG}")
    server.serve_forever()
    return 0


def parse_query(query: str) -> dict[str, str]:
    from urllib.parse import parse_qs

    pairs: dict[str, str] = {}
    for key, values in parse_qs(query, keep_blank_values=True).items():
        pairs[key] = values[-1] if values else ""
    return pairs


def parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


if __name__ == "__main__":
    raise SystemExit(main())
