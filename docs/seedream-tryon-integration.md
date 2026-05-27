# Seedream 4.0 美甲试戴接入说明

## 当前目标

构建后端任务框架：

> 读取用户点击的可试戴款式图，理解每个手指上的美甲款式，将该美甲款式应用到用户上传的手部图片上，生成融合效果图。

## 已接入模块

- `backend/config.py`：Seedream/Ark 配置。
- `backend/seedream_client.py`：Seedream 图片生成客户端。
- `backend/tryon_service.py`：美甲试戴任务编排、prompt 构建和任务日志。
- `backend/server.py`：新增 `/api/tryon` 接口。
- `frontend/app.js`：点击款式后优先调用 `http://127.0.0.1:8000/api/tryon`，失败时降级为本地 Canvas 预览。

## 环境变量

不要把真实 API Key 写入代码仓库。启动后端前，在 PowerShell 中设置：

```powershell
$env:ARK_API_KEY="你的 Ark API Key"
$env:SEEDREAM_MODEL="doubao-seedream-4-0-250828"
```

可选配置：

```powershell
$env:SEEDREAM_API_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"
$env:SEEDREAM_SIZE="1K"
$env:SEEDREAM_TIMEOUT_SECONDS="75"
$env:SEEDREAM_WATERMARK="false"
```

速度优先时建议使用 `1K`；需要展示级大图时再临时切回 `2K`。前端会在上传前把手图压缩为长边约 1280px 的 JPEG，以减少请求体积和 Seedream 侧的输入处理时间。

## 启动方式

```powershell
python backend\server.py
```

页面仍然可以从本地文件打开：

```text
frontend/index.html
```

当前前端会直接请求：

```text
http://127.0.0.1:8000/api/tryon
```

## 请求结构

前端会发送：

```json
{
  "sessionId": "local-session-id",
  "handImageDataUrl": "data:image/png;base64,...",
  "style": {
    "styleId": "style_001",
    "title": "款式 01",
    "styleOriginalUrl": "http://...",
    "styleOriginalPath": "../data/raw/images/nail_styles_original/style_001_original.png"
  },
  "createdAt": "2026-05-15T..."
}
```

## Prompt 框架

后端会构造如下任务语义：

- 保持用户手部照片的构图、肤色、光照、背景、手指数量、手指形状和指甲轮廓不变。
- 只修改用户手部照片中的可见指甲区域。
- 从款式参考图中提取美甲颜色、纹理、图案、光泽、渐变、法式边、亮片或装饰元素。
- 将参考款式自然贴合到用户手图的每个指甲上，符合指甲边界、角度和透视。
- 不增加额外手指、文字、logo、水印、戒指、手链或新的背景元素。

## 日志

点击与上传事件：

```text
backend/data/click_events.jsonl
```

试戴任务日志：

```text
backend/data/tryon_tasks.jsonl
```

## 当前限制

当前本地上传的手图会以 data URL 传给后端，再由后端传给 Seedream。如果 Ark/Seedream 当前接口只接受公网图片 URL，那么需要增加一层图片上传：

1. 用户上传手图。
2. 后端保存图片。
3. 后端上传到对象存储或临时公网文件服务。
4. 将公网 URL 传给 Seedream。

这层已经在结构上预留，后续只需要替换 `tryon_service.py` 中的图片引用生成逻辑。
