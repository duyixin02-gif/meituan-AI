from __future__ import annotations

import base64
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import SEEDREAM_USE_STYLE_DETAIL_REF
from seedream_client import SeedreamClient, SeedreamConfigError, SeedreamRequestError


ROOT = Path(__file__).resolve().parents[1]
TASK_LOG = ROOT / "backend" / "data" / "tryon_tasks.jsonl"
RESULT_DIR = ROOT / "backend" / "data" / "tryon_results"


def build_tryon_prompt(
    style_title: str,
    style_id: str,
    has_detail_reference: bool = False,
    strategy: str = "full_image_fast",
    nail_shape_policy: str = "match_reference_shape",
) -> str:
    detail_reference_text = (
        "\n第三张图是款式细节参考图，只用于补充小图案、亮片密度、线条、饰品和质感细节；不要复制第三张图的手、背景或构图。"
        if has_detail_reference
        else ""
    )
    strategy_text = (
        "\n第一张图是从用户原图裁出的手部局部图。请保持这个局部图的手部轮廓、裁剪范围、局部背景和画面比例不变，输出同构图局部结果，便于后续贴回用户原图。"
        if strategy == "high_precision_crop"
        else "\n第一张图是用户完整手部照片。请直接在原图构图上完成试戴，不要重新生成另一张手图。"
    )
    shape_texts = {
        "extend_and_reshape": "本款属于长甲/造型甲：允许在每个原始指甲的自然生长方向上适度延长并重塑甲尖，尽量还原参考图的甲长、甲型和甲尖形状；延长部分必须连接在原指甲上，不能改变手指长度、皮肤轮廓或生成漂浮甲片。",
        "preserve_natural": "本款属于短甲/自然甲：保持用户原始指甲长度和轮廓，只迁移颜色、图案、质感和装饰，不要明显延长或改变甲型。",
        "match_reference_shape": "根据参考图判断甲型：在不改变手指和皮肤的前提下，适度匹配参考图的甲长、甲尖和轮廓；如果参考图是长甲，可轻微延长指甲自由缘。",
    }
    nail_shape_text = shape_texts.get(nail_shape_policy, shape_texts["match_reference_shape"])
    return f"""
你是严谨的美甲试戴图像编辑助手。必须以第一张图“用户手部照片”为唯一底图，第二张图“款式参考图”只用于提取美甲设计。{detail_reference_text}{strategy_text}

任务：将参考款式 {style_title}（{style_id}）贴到用户手部照片的可见指甲上。

硬性要求：
1. 保持第一张图的手部姿势、手指数量、肤色、光照、背景、构图、相机角度和画面比例不变。
2. 第一张图背景即使复杂也必须原样保留；不要简化、替换、模糊或重绘背景。
3. 只编辑每个可见指甲区域，不重绘整只手，不换手，不换背景，不改变皮肤、饰品或手指形状。
4. 第二张/第三张图里的背景、手型、肤色、手指朝向和左右手信息都不是目标，只提取指甲上的款式设计。
5. 如果用户手图与款式图左右手不一致，按拇指到小指的相对顺序映射；必要时镜像或旋转款式元素来贴合第一张图的指甲方向。
6. 从参考图提取并尽量逐指甲还原：底色、渐变方向、法式边宽度、猫眼光带、亮片密度、小图案位置、金属线条、钻饰或装饰。
7. 甲型策略：{nail_shape_text}
8. 款式要贴合指甲根部、弧度、角度和透视；边缘自然融合，但不要涂到甲沟或皮肤。
9. 细节优先忠实于参考款式；如果细节很小，保留其相对位置、颜色和数量感，不要改成另一种相近款。
10. 禁止新增文字、logo、水印、额外手指、戒指、手链或新背景。

输出：一张真实自然的美甲试戴结果图。
""".strip()


def estimate_reference_bytes(reference: str) -> int | None:
    if reference.startswith("data:") and "," in reference:
        return int((len(reference.split(",", 1)[1]) * 3) / 4)
    return None


def data_url_from_local_path(local_path: str) -> str:
    normalized = local_path.replace("\\", "/").lstrip("/")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    path = (ROOT / normalized).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {local_path}")
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def local_reference_from_style(style: dict[str, Any], keys: tuple[str, ...]) -> tuple[str | None, str]:
    for key in keys:
        if style.get(key):
            try:
                return data_url_from_local_path(style[key]), key
            except FileNotFoundError:
                continue
    return None, "missing"


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class TryonService:
    def __init__(self) -> None:
        self.client = SeedreamClient()

    def create_tryon(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = f"tryon_{uuid.uuid4().hex}"
        style = payload.get("style") or {}
        hand_processing = payload.get("handProcessing") or {}
        strategy = hand_processing.get("strategy") or "full_image_fast"
        nail_shape_policy = (
            payload.get("nailShapePolicy")
            or style.get("nailShapePolicy")
            or "match_reference_shape"
        )
        style_id = style.get("styleId") or "unknown_style"
        style_title = style.get("title") or style_id

        hand_reference = payload.get("handImageDataUrl") or payload.get("handReferenceUrl")
        style_reference, style_reference_source = local_reference_from_style(
            style,
            ("styleOriginalPath", "stylePreviewPath", "styleEnhancedPath"),
        )
        if not style_reference:
            style_reference = (
                style.get("styleSourceUrl")
                or style.get("styleOriginalUrl")
                or payload.get("styleReferenceUrl")
            )
            style_reference_source = "url" if style_reference else "missing"

        style_detail_reference = None
        style_detail_source = "disabled"
        if SEEDREAM_USE_STYLE_DETAIL_REF:
            style_detail_reference, style_detail_source = local_reference_from_style(
                style,
                ("styleEnhancedPath",),
            )
            if style_detail_reference == style_reference:
                style_detail_reference = None
                style_detail_source = "duplicate"
            if not style_detail_reference and style.get("styleEnhancedUrl"):
                style_detail_reference = style.get("styleEnhancedUrl")
                style_detail_source = "styleEnhancedUrl"
            if style_detail_reference == style_reference:
                style_detail_reference = None
                style_detail_source = "duplicate"

        if not hand_reference:
            raise ValueError("Missing hand image reference.")
        if not style_reference:
            raise ValueError("Missing style image reference.")

        image_references = [hand_reference, style_reference]
        if style_detail_reference:
            image_references.append(style_detail_reference)

        prompt = build_tryon_prompt(
            style_title=style_title,
            style_id=style_id,
            has_detail_reference=bool(style_detail_reference),
            strategy=strategy,
            nail_shape_policy=nail_shape_policy,
        )
        task_record = {
            "taskId": task_id,
            "status": "submitted",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "sessionId": payload.get("sessionId"),
            "styleId": style_id,
            "handProcessing": hand_processing,
            "nailShapePolicy": nail_shape_policy,
            "prompt": prompt,
            "inputModes": {
                "hand": "data_url" if str(hand_reference).startswith("data:") else "url",
                "style": "data_url" if str(style_reference).startswith("data:") else "url",
                "styleDetail": "data_url"
                if style_detail_reference and str(style_detail_reference).startswith("data:")
                else "url"
                if style_detail_reference
                else "none",
            },
            "referenceSources": {
                "hand": "payload.handImageDataUrl"
                if str(hand_reference).startswith("data:")
                else "payload.handReferenceUrl",
                "style": style_reference_source,
                "styleDetail": style_detail_source,
            },
            "inputBytes": {
                "hand": estimate_reference_bytes(str(hand_reference)),
                "style": estimate_reference_bytes(str(style_reference)),
                "styleDetail": estimate_reference_bytes(str(style_detail_reference))
                if style_detail_reference
                else None,
            },
        }
        append_jsonl(TASK_LOG, task_record)

        try:
            result = self.client.generate_tryon(
                prompt=prompt,
                image_references=image_references,
            )
        except (SeedreamConfigError, SeedreamRequestError) as exc:
            append_jsonl(
                TASK_LOG,
                {
                    **task_record,
                    "status": "failed",
                    "failedAt": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                },
            )
            raise

        result_record = {
            **task_record,
            "status": "completed",
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "resultImageUrl": result.image_url,
            "hasBase64Result": bool(result.b64_json),
            "rawResponse": result.raw_response,
        }
        append_jsonl(TASK_LOG, result_record)

        return {
            "ok": True,
            "taskId": task_id,
            "status": "completed",
            "handProcessing": hand_processing,
            "nailShapePolicy": nail_shape_policy,
            "resultImageUrl": result.image_url,
            "resultImageBase64": result.b64_json,
        }
