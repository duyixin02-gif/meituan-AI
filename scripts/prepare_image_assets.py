from __future__ import annotations

import csv
import hashlib
import json
import shutil
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATTERN = "命题三美甲评测数据*.xlsx"
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def col_to_idx(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    idx = 0
    for ch in letters:
        idx = idx * 26 + ord(ch) - ord("A") + 1
    return idx - 1


def read_xlsx_rows(path: Path) -> list[list[list[str]]]:
    with ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", NS):
                shared.append("".join((t.text or "") for t in si.findall(".//a:t", NS)))

        sheets = sorted(
            name for name in zf.namelist() if name.startswith("xl/worksheets/sheet")
        )
        all_rows = []
        for sheet in sheets:
            root = ET.fromstring(zf.read(sheet))
            rows = []
            for row in root.findall(".//a:row", NS):
                values = []
                for cell in row.findall("a:c", NS):
                    idx = col_to_idx(cell.attrib["r"])
                    while len(values) <= idx:
                        values.append("")
                    value_node = cell.find("a:v", NS)
                    if value_node is None:
                        value = ""
                    elif cell.attrib.get("t") == "s":
                        value = shared[int(value_node.text)]
                    else:
                        value = value_node.text or ""
                    values[idx] = value
                rows.append(values)
            all_rows.append(rows)
        return all_rows


def extension_from_url(url: str) -> str:
    match = re.search(r"\.(png|jpg|jpeg|webp)(?:$|\?)", url, re.IGNORECASE)
    if not match:
        return ".jpg"
    ext = match.group(1).lower()
    return ".jpg" if ext == "jpeg" else f".{ext}"


def download(url: str, output_path: Path) -> tuple[bool, str]:
    if output_path.exists() and output_path.stat().st_size > 0:
        return True, "exists"

    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=30) as response:
            output_path.write_bytes(response.read())
        return True, "downloaded"
    except URLError:
        return False, "network_unavailable_or_blocked"
    except TimeoutError:
        return False, "timeout"


def main() -> int:
    workbook_candidates = list(ROOT.glob(WORKBOOK_PATTERN))
    if not workbook_candidates:
        print(f"No workbook matched {WORKBOOK_PATTERN}", file=sys.stderr)
        return 1

    workbook = workbook_candidates[0]
    sheets = read_xlsx_rows(workbook)
    if len(sheets) < 2:
        print("Workbook should contain at least two sheets.", file=sys.stderr)
        return 1

    image_dirs = {
        "hand": ROOT / "data" / "raw" / "images" / "hands",
        "style_original": ROOT / "data" / "raw" / "images" / "nail_styles_original",
        "style_enhanced": ROOT / "data" / "raw" / "images" / "nail_styles_enhanced",
    }
    for directory in image_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    processed_dir = ROOT / "data" / "processed"
    schemas_dir = ROOT / "data" / "schemas"
    processed_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir.mkdir(parents=True, exist_ok=True)

    sheet1 = sheets[0][1:]
    sheet2 = sheets[1][1:]

    style_lookup = {}
    for row in sheet2:
        if len(row) >= 3:
            idx, original_url, enhanced_url = row[:3]
            style_lookup[enhanced_url] = {
                "style_id": f"style_{int(float(idx)):03d}",
                "original_url": original_url,
                "enhanced_url": enhanced_url,
            }

    assets = []
    pairs = []

    def add_asset(asset_type: str, asset_id: str, url: str) -> str:
        ext = extension_from_url(url)
        filename = f"{asset_id}{ext}"
        local_path = image_dirs[asset_type] / filename
        rel_path = local_path.relative_to(ROOT).as_posix()
        assets.append(
            {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "source_url": url,
                "local_path": rel_path,
                "source_hash": hashlib.sha1(url.encode("utf-8")).hexdigest(),
            }
        )
        return rel_path

    for i, row in enumerate(sheet1, start=1):
        if len(row) < 2:
            continue
        hand_url, enhanced_url = row[:2]
        pair_id = f"pair_{i:03d}"
        style = style_lookup.get(
            enhanced_url,
            {
                "style_id": f"style_{i:03d}",
                "original_url": "",
                "enhanced_url": enhanced_url,
            },
        )
        hand_id = f"hand_{i:03d}" if hand_url else ""
        hand_path = add_asset("hand", hand_id, hand_url) if hand_url else ""
        original_path = (
            add_asset("style_original", f"{style['style_id']}_original", style["original_url"])
            if style["original_url"]
            else ""
        )
        enhanced_path = add_asset(
            "style_enhanced", f"{style['style_id']}_enhanced", style["enhanced_url"]
        )

        pairs.append(
            {
                "pair_id": pair_id,
                "hand_id": hand_id,
                "style_id": style["style_id"],
                "hand_url": hand_url,
                "style_original_url": style["original_url"],
                "style_enhanced_url": style["enhanced_url"],
                "hand_path": hand_path,
                "style_original_path": original_path,
                "style_enhanced_path": enhanced_path,
            }
        )

    url_groups = {}
    for asset in assets:
        if asset["source_url"]:
            url_groups.setdefault(asset["source_url"], []).append(asset)
    download_results = []
    for source_url, grouped_assets in url_groups.items():
        primary = grouped_assets[0]
        primary_path = ROOT / primary["local_path"]
        ok, status = download(source_url, primary_path)
        primary["download_status"] = status if ok else "failed"
        primary["download_error"] = "" if ok else status
        primary["file_size"] = primary_path.stat().st_size if primary_path.exists() else 0
        download_results.append(primary)

        for asset in grouped_assets[1:]:
            local_path = ROOT / asset["local_path"]
            if ok and primary_path.exists() and primary_path.resolve() != local_path.resolve():
                local_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(primary_path, local_path)
                asset["download_status"] = "copied_from_duplicate_url"
                asset["download_error"] = ""
            else:
                asset["download_status"] = primary["download_status"]
                asset["download_error"] = primary["download_error"]
            asset["file_size"] = local_path.stat().st_size if local_path.exists() else 0
            download_results.append(asset)

    asset_fields = [
        "asset_id",
        "asset_type",
        "source_url",
        "local_path",
        "source_hash",
        "download_status",
        "download_error",
        "file_size",
    ]
    pair_fields = [
        "pair_id",
        "hand_id",
        "style_id",
        "hand_url",
        "style_original_url",
        "style_enhanced_url",
        "hand_path",
        "style_original_path",
        "style_enhanced_path",
    ]

    with (processed_dir / "image_assets.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=asset_fields)
        writer.writeheader()
        writer.writerows(download_results)

    with (processed_dir / "image_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(pairs)

    with (processed_dir / "image_pairs.jsonl").open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    tryon_pairs = [pair for pair in pairs if pair["hand_path"] and pair["style_enhanced_path"]]
    with (processed_dir / "tryon_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(tryon_pairs)

    style_catalog_fields = [
        "style_id",
        "style_original_path",
        "style_enhanced_path",
        "dominant_color",
        "style_tags",
        "nail_shape",
        "complexity_level",
        "suitable_scenes",
        "operation_role",
        "notes",
    ]
    with (processed_dir / "style_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=style_catalog_fields)
        writer.writeheader()
        for pair in pairs:
            writer.writerow(
                {
                    "style_id": pair["style_id"],
                    "style_original_path": pair["style_original_path"],
                    "style_enhanced_path": pair["style_enhanced_path"],
                    "dominant_color": "",
                    "style_tags": "",
                    "nail_shape": "",
                    "complexity_level": "",
                    "suitable_scenes": "",
                    "operation_role": "",
                    "notes": "",
                }
            )

    schema = {
        "source_workbook_pattern": "meituan-nail-evaluation-data-xlsx",
        "generated_files": [
            "data/processed/image_assets.csv",
            "data/processed/image_pairs.csv",
            "data/processed/image_pairs.jsonl",
            "data/processed/tryon_pairs.csv",
            "data/processed/style_catalog.csv",
        ],
        "image_directories": {key: path.relative_to(ROOT).as_posix() for key, path in image_dirs.items()},
        "asset_count": len(download_results),
        "unique_url_count": len(url_groups),
        "pair_count": len(pairs),
        "tryon_pair_count": len(tryon_pairs),
        "notes": [
            "Only source URLs from the provided workbook are used.",
            "No synthetic test images are created.",
            "Temporary files should be removed after validation if created in future experiments.",
        ],
    }
    (schemas_dir / "image-assets-schema.json").write_text(
        json.dumps(schema, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    downloaded = sum(
        1
        for asset in download_results
        if asset["download_status"] in {"downloaded", "exists", "copied_from_duplicate_url"}
    )
    failed = len(download_results) - downloaded
    print(f"Workbook: {workbook.name}")
    print(f"Pairs: {len(pairs)}")
    print(f"Assets: {len(download_results)}")
    print(f"Downloaded or existing: {downloaded}")
    print(f"Failed: {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
