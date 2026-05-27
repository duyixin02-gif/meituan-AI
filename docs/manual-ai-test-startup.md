# AI 融图与数据分析手动测试启动说明

本文用于本地手动测试，确认两类能力都已开启：

- AI 融图：`POST /api/tryon`，调用 Ark / Seedream 生成美甲试戴融合图。
- 数据分析：`/api/data-agent/*` 和 `/api/ops/*`，整理点击事件、生成运营看板和策略建议。

> 注意：当前数据分析与运营策略是本地规则和统计分析链路，不需要 Ark API Key；AI 融图需要 `ARK_API_KEY`。

## 1. 打开 PowerShell 并进入项目

```powershell
cd F:\project\meituan
```

## 2. 配置 AI 融图环境变量

把 `你的 Ark API Key` 换成真实 Key。不要把 Key 写入代码或提交到仓库。

```powershell
$env:ARK_API_KEY="你的 Ark API Key"
$env:SEEDREAM_API_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"
$env:SEEDREAM_MODEL="doubao-seedream-4-0-250828"
$env:SEEDREAM_SIZE="1K"
$env:SEEDREAM_TIMEOUT_SECONDS="75"
$env:SEEDREAM_MAX_RETRIES="2"
$env:SEEDREAM_USE_STYLE_DETAIL_REF="true"
$env:SEEDREAM_WATERMARK="false"
```

说明：

- `SEEDREAM_SIZE=1K` 用于更快的试戴预览。
- 如果需要展示级大图，可以临时改成 `2K`，但响应会更慢。
- 如果接口长时间无响应，可以把 `SEEDREAM_TIMEOUT_SECONDS` 改成 `120`。
- `SEEDREAM_MAX_RETRIES=2` 会对网络抖动或 5xx 错误做有限重试；401/参数错误不会重试。
- `SEEDREAM_USE_STYLE_DETAIL_REF=true` 会额外传入款式增强图作为细节参考，可提升复杂背景、左右手不一致和细节复刻场景的稳定性；如需极限速度可改成 `false`。

## 3. 启动后端服务

推荐使用项目脚本启动，它会处理端口检查和日志输出：

```powershell
.\scripts\start_user_app.ps1
```

启动成功时会看到类似：

```text
Started: http://127.0.0.1:8000/frontend/index.html
PID: 12345
```

如果你想直接前台启动，也可以用：

```powershell
python backend\server.py
```

前台启动后不要关闭这个 PowerShell 窗口。

## 4. 健康检查

确认后端已启动：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/health |
  Select-Object -ExpandProperty Content
```

返回里应包含：

```json
"ok": true
```

并能看到这些端点：

- `/api/tryon`
- `/api/data-agent/run`
- `/api/data-agent/summary`
- `/api/ops/merchant-dashboard`
- `/api/ops/platform-trends`
- `/api/ops/strategy/run`
- `/api/ops/demo-data`

## 5. 手动测试 AI 融图

当前用户端采用三层策略：

1. 高精度方案：前端先用 Canvas 从用户图中裁出手部候选区域，后端优先对 crop 图调用 Seedream，成功后前端尝试贴回用户原图背景。
2. 快速备选：如果高精度调用或回贴失败，自动改用完整手图调用 Seedream。
3. 兜底方案：如果 AI 调用失败，页面保留本地 Canvas 预览。

### 方式 A：通过用户端页面测试

打开：

```text
http://127.0.0.1:8000/frontend/index.html
```

操作步骤：

1. 上传一张手部照片。
2. 选择右侧任意美甲款式。
3. 等待状态提示“AI 试戴效果已生成”。
4. 页面中出现 AI 融合结果图，即表示 `/api/tryon` 已走通。

注意：如果没有上传手图，只用“示例手图”，当前前端不会调用 AI 融图接口，会使用本地 Canvas 预览。

### 方式 B：直接调用 `/api/tryon`

这条命令使用已有公网样例图 URL 测试，适合快速确认后端和 Seedream 是否连通：

```powershell
$body = @{
  sessionId = "manual-ai-test"
  handReferenceUrl = "http://p0.meituan.net/pilotimages/b9632e3a699fdb63a1a6139bbfd6bf0d2159483.png"
  style = @{
    styleId = "style_001"
    title = "款式 01"
    styleOriginalUrl = "http://p0.meituan.net/pilotimages/8491d190aeb8f44e32f6b278535bf2b41075477.png"
  }
  createdAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 6

Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/tryon `
  -Method POST `
  -ContentType "application/json" `
  -Body $body |
  Select-Object -ExpandProperty Content
```

成功时返回应包含：

```json
{
  "ok": true,
  "status": "completed",
  "resultImageUrl": "https://..."
}
```

同时检查日志：

```powershell
Get-Content backend\data\tryon_tasks.jsonl -Tail 2
```

能看到 `submitted` 和 `completed` 两条记录，表示 AI 融图链路已开启。记录里的 `handProcessing.strategy` 会显示本次使用了 `high_precision_crop` 还是 `full_image_fast`。

## 6. 手动测试数据分析

### 6.1 生成演示运营数据

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/ops/demo-data `
  -Method POST |
  Select-Object -ExpandProperty Content
```

成功时通常会返回 `ok: true` 或写入记录数量。

### 6.2 运行用户行为数据处理 Agent

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/data-agent/run `
  -Method POST |
  Select-Object -ExpandProperty Content
```

然后读取摘要：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/data-agent/summary |
  Select-Object -ExpandProperty Content
```

确认输出文件存在：

```powershell
Get-ChildItem backend\data\structured_click_*
```

应看到：

- `structured_click_features.jsonl`
- `structured_click_summary.json`

### 6.3 测试运营看板数据接口

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/api/ops/merchant-dashboard?merchantId=merchant_001&windowDays=7" |
  Select-Object -ExpandProperty Content
```

再测试平台趋势：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/api/ops/platform-trends?windowDays=7" |
  Select-Object -ExpandProperty Content
```

### 6.4 测试策略分析接口

```powershell
$strategyBody = @{
  merchantId = "merchant_001"
  windowDays = 7
} | ConvertTo-Json

Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/ops/strategy/run `
  -Method POST `
  -ContentType "application/json" `
  -Body $strategyBody |
  Select-Object -ExpandProperty Content
```

成功时返回里应包含：

- `recommendations`
- `strategyType`
- `title`
- `reason`
- `confidence`

## 7. 页面验证

用户端试戴页面：

```text
http://127.0.0.1:8000/frontend/index.html
```

商家数据分析页面：

```text
http://127.0.0.1:8000/frontend/merchant-dashboard.html
```

建议测试顺序：

1. 先打开用户端页面，上传手图并生成一次 AI 试戴。
2. 点击、收藏、加入对比，产生一些前端行为事件。
3. 调用 `/api/data-agent/run`。
4. 打开商家后台页面，确认看板、趋势和策略推荐能加载。

## 8. 常见问题排查

### AI 融图返回 `seedream_not_configured`

说明没有设置 `ARK_API_KEY`，重新在启动后端的同一个 PowerShell 窗口里执行：

```powershell
$env:ARK_API_KEY="你的 Ark API Key"
```

然后重启后端。

### AI 融图返回 `seedream_request_failed`

优先检查：

- `ARK_API_KEY` 是否有效。
- 当前网络是否能访问 Ark / Seedream。
- `SEEDREAM_MODEL` 是否和 Ark 控制台开通的模型一致。
- 如果使用图片 URL，Seedream 是否能访问这些 URL。

查看后端日志：

```powershell
Get-Content backend\server.err.log -Tail 80
```

### 页面显示本地 Canvas 预览，而不是 AI 结果

常见原因：

- 没有上传手图，只用了示例手图。
- 后端没启动。
- `ARK_API_KEY` 缺失或 Seedream 请求失败。

检查：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/health |
  Select-Object -ExpandProperty Content
```

### 数据分析没有内容

先生成演示数据：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/ops/demo-data -Method POST
```

再运行：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/data-agent/run -Method POST
```

### 端口 8000 被占用

查看占用进程：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Where-Object { $_.State -eq "Listen" }
```

如果是旧的本项目服务，可以关闭对应 PID 后重新启动。

## 9. 一键冒烟测试清单

按顺序执行：

```powershell
cd F:\project\meituan

$env:ARK_API_KEY="你的 Ark API Key"
$env:SEEDREAM_API_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"
$env:SEEDREAM_MODEL="doubao-seedream-4-0-250828"
$env:SEEDREAM_SIZE="1K"
$env:SEEDREAM_TIMEOUT_SECONDS="75"
$env:SEEDREAM_MAX_RETRIES="2"
$env:SEEDREAM_USE_STYLE_DETAIL_REF="true"
$env:SEEDREAM_WATERMARK="false"

.\scripts\start_user_app.ps1

Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/health |
  Select-Object -ExpandProperty Content

Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/ops/demo-data -Method POST |
  Select-Object -ExpandProperty Content

Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/data-agent/run -Method POST |
  Select-Object -ExpandProperty Content
```

然后打开：

```text
http://127.0.0.1:8000/frontend/index.html
http://127.0.0.1:8000/frontend/merchant-dashboard.html
```

完成一次上传手图、选择款式、生成 AI 试戴，并确认商家后台有数据即可。
