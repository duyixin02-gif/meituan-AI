from __future__ import annotations

import os


ARK_API_KEY_ENV = "ARK_API_KEY"

SEEDREAM_API_URL = os.environ.get(
    "SEEDREAM_API_URL",
    "https://ark.cn-beijing.volces.com/api/v3/images/generations",
)
SEEDREAM_MODEL = os.environ.get("SEEDREAM_MODEL", "doubao-seedream-4-0-250828")
SEEDREAM_SIZE = os.environ.get("SEEDREAM_SIZE", "1K")
SEEDREAM_TIMEOUT_SECONDS = int(os.environ.get("SEEDREAM_TIMEOUT_SECONDS", "75"))
SEEDREAM_MAX_RETRIES = int(os.environ.get("SEEDREAM_MAX_RETRIES", "2"))
SEEDREAM_USE_STYLE_DETAIL_REF = (
    os.environ.get("SEEDREAM_USE_STYLE_DETAIL_REF", "true").lower() == "true"
)
SEEDREAM_WATERMARK = os.environ.get("SEEDREAM_WATERMARK", "false").lower() == "true"
