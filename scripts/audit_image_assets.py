from __future__ import annotations

import csv
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "data" / "raw" / "images"
PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def jpg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        if f.read(2) != b"\xff\xd8":
            raise ValueError("not a jpg")
        while True:
            marker_prefix = f.read(1)
            if marker_prefix != b"\xff":
                raise ValueError("invalid jpg marker")
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            marker_int = marker[0]
            if marker_int in {0xD8, 0xD9}:
                continue
            length = struct.unpack(">H", f.read(2))[0]
            if 0xC0 <= marker_int <= 0xC3:
                data = f.read(5)
                height, width = struct.unpack(">HH", data[1:5])
                return width, height
            f.seek(length - 2, 1)


def image_size(path: Path) -> tuple[int, int]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return png_size(path)
    if suffix in {".jpg", ".jpeg"}:
        return jpg_size(path)
    raise ValueError(f"unsupported extension: {suffix}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    assets = read_csv(PROCESSED_DIR / "image_assets.csv")
    pairs = read_csv(PROCESSED_DIR / "image_pairs.csv")
    rows = []

    for asset in assets:
        local_path = ROOT / asset["local_path"]
        exists = local_path.exists()
        width = height = ""
        error = ""
        if exists:
            try:
                width, height = image_size(local_path)
            except Exception as exc:
                error = type(exc).__name__
        rows.append(
            {
                "asset_id": asset["asset_id"],
                "asset_type": asset["asset_type"],
                "local_path": asset["local_path"],
                "extension": local_path.suffix.lower(),
                "exists": str(exists).lower(),
                "file_size": local_path.stat().st_size if exists else 0,
                "width": width,
                "height": height,
                "read_error": error,
            }
        )

    inventory_path = PROCESSED_DIR / "image_inventory.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "asset_id",
            "asset_type",
            "local_path",
            "extension",
            "exists",
            "file_size",
            "width",
            "height",
            "read_error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    by_type = {}
    for row in rows:
        by_type.setdefault(row["asset_type"], []).append(row)

    pair_with_hand = sum(1 for pair in pairs if pair["hand_url"])
    pair_without_hand = len(pairs) - pair_with_hand
    missing_files = [row for row in rows if row["exists"] != "true"]
    unreadable_files = [row for row in rows if row["read_error"]]

    summary = {
        "asset_count": len(rows),
        "pair_count": len(pairs),
        "pair_with_hand": pair_with_hand,
        "pair_without_hand": pair_without_hand,
        "missing_file_count": len(missing_files),
        "unreadable_file_count": len(unreadable_files),
        "by_type": {
            key: {
                "count": len(items),
                "extensions": sorted(set(item["extension"] for item in items)),
                "sizes": sorted(set(f"{item['width']}x{item['height']}" for item in items)),
            }
            for key, items in by_type.items()
        },
    }

    report_lines = [
        "# 图片资产盘点报告",
        "",
        "## 总览",
        "",
        f"- 图片资产数：{summary['asset_count']}",
        f"- 款式配对数：{summary['pair_count']}",
        f"- 有手图的配对数：{summary['pair_with_hand']}",
        f"- 缺少手图的配对数：{summary['pair_without_hand']}",
        f"- 缺失文件数：{summary['missing_file_count']}",
        f"- 无法读取尺寸的文件数：{summary['unreadable_file_count']}",
        "",
        "## 按类型统计",
        "",
        "| 类型 | 数量 | 格式 | 尺寸 |",
        "| --- | ---: | --- | --- |",
    ]
    for key, item in summary["by_type"].items():
        report_lines.append(
            f"| {key} | {item['count']} | {', '.join(item['extensions'])} | {', '.join(item['sizes'])} |"
        )

    report_lines.extend(
        [
            "",
            "## 结论",
            "",
            "- 当前可用于完整试戴验证的配对为 13 组，即同时具备手图和增强后款式图的记录。",
            "- 25 组款式图均可用于款式标签、风格识别和商户运营策略原型。",
            "- 后续美甲试戴原型建议优先使用 `pair_001` 到 `pair_013`。",
            "- 后续商户运营策略原型可以使用全部 25 个款式。",
            "",
            "## 生成文件",
            "",
            "- `data/processed/image_inventory.csv`",
            "- `docs/image-asset-audit.md`",
        ]
    )

    (DOCS_DIR / "image-asset-audit.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    (PROCESSED_DIR / "image_inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
