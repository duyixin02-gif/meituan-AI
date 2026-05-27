from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import (
    ARK_API_KEY_ENV,
    SEEDREAM_API_URL,
    SEEDREAM_MODEL,
    SEEDREAM_MAX_RETRIES,
    SEEDREAM_SIZE,
    SEEDREAM_TIMEOUT_SECONDS,
    SEEDREAM_WATERMARK,
)


class SeedreamConfigError(RuntimeError):
    pass


class SeedreamRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedreamResult:
    image_url: str | None
    b64_json: str | None
    raw_response: dict[str, Any]


class SeedreamClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or os.environ.get(ARK_API_KEY_ENV) or "").strip()
        if self.api_key.lower().startswith("bearer "):
            self.api_key = self.api_key[7:].strip()
        if not self.api_key:
            raise SeedreamConfigError(
                f"Missing {ARK_API_KEY_ENV}. Set it before starting the backend server."
            )
        parsed_url = urlparse(SEEDREAM_API_URL)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise SeedreamConfigError(
                f"Invalid SEEDREAM_API_URL: {SEEDREAM_API_URL!r}. Use a full https URL."
            )

    def generate_tryon(self, prompt: str, image_references: list[str]) -> SeedreamResult:
        payload = {
            "model": SEEDREAM_MODEL,
            "prompt": prompt,
            "image": image_references,
            "size": SEEDREAM_SIZE,
            "sequential_image_generation": "disabled",
            "response_format": "url",
            "stream": False,
            "watermark": SEEDREAM_WATERMARK,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        attempts = max(1, SEEDREAM_MAX_RETRIES + 1)
        last_error: SeedreamRequestError | None = None
        raw: dict[str, Any] | None = None

        for attempt in range(1, attempts + 1):
            request = Request(
                SEEDREAM_API_URL,
                data=data,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urlopen(request, timeout=SEEDREAM_TIMEOUT_SECONDS) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                error = SeedreamRequestError(f"Seedream HTTP {exc.code}: {body}")
                if exc.code < 500 or attempt >= attempts:
                    raise error from exc
                last_error = error
            except URLError as exc:
                last_error = SeedreamRequestError(f"Seedream network error: {exc.reason}")
            except TimeoutError:
                last_error = SeedreamRequestError("Seedream request timed out")

            if attempt < attempts:
                time.sleep(0.8 * attempt)

        if raw is None:
            raise last_error or SeedreamRequestError("Seedream request failed")

        first = (raw.get("data") or [{}])[0]
        return SeedreamResult(
            image_url=first.get("url"),
            b64_json=first.get("b64_json"),
            raw_response=raw,
        )
