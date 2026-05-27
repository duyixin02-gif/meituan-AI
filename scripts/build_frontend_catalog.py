from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRYON_PAIRS = ROOT / "data" / "processed" / "tryon_pairs.csv"
CATALOG_OUT = ROOT / "frontend" / "assets" / "catalog.json"
CATALOG_JS_OUT = ROOT / "frontend" / "assets" / "catalog.js"


def main() -> int:
    CATALOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    with TRYON_PAIRS.open("r", encoding="utf-8", newline="") as f:
        pairs = list(csv.DictReader(f))

    styles = []
    for index, pair in enumerate(pairs, start=1):
        styles.append(
            {
                "pairId": pair["pair_id"],
                "styleId": pair["style_id"],
                "title": f"款式 {index:02d}",
                "subtitle": "AI 可试戴款",
                "handPath": "../" + pair["hand_path"].replace("\\", "/"),
                "handSourceUrl": pair["hand_url"],
                "styleOriginalUrl": pair["style_original_url"],
                "styleEnhancedUrl": pair["style_enhanced_url"],
                "styleOriginalPath": "../" + pair["style_original_path"].replace("\\", "/"),
                "styleEnhancedPath": "../" + pair["style_enhanced_path"].replace("\\", "/"),
                "stylePreviewPath": "../" + pair["style_original_path"].replace("\\", "/"),
            }
        )

    payload = {
        "source": "data/processed/tryon_pairs.csv",
        "count": len(styles),
        "styles": styles,
    }
    CATALOG_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    CATALOG_JS_OUT.write_text(
        "window.NAIL_TRYON_CATALOG = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {CATALOG_OUT.relative_to(ROOT)} with {len(styles)} styles")
    print(f"Wrote {CATALOG_JS_OUT.relative_to(ROOT)} with {len(styles)} styles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
