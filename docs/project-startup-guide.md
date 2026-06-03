# 项目服务启动完整流程

本文档说明如何在本地启动当前项目服务，并完成基础验证。项目根目录为：

```powershell
F:\project\meituan
```

## 1. 项目启动方式概览

当前项目是一个 Python 后端服务加静态前端页面：

- 后端入口：`backend\server.py`
- 推荐启动脚本：`scripts\start_user_app.ps1`
- 默认服务地址：`http://127.0.0.1:8000`
- 平台入口页面：`http://127.0.0.1:8000/frontend/index.html`
- 用户端页面：`http://127.0.0.1:8000/frontend/user-app.html`
- 商家端页面：`http://127.0.0.1:8000/frontend/merchant-dashboard.html`

后端服务启动后会同时提供 API 和静态页面访问能力，因此不需要单独启动前端开发服务器。

## 2. 启动前准备

### 2.1 确认 Python 可用

打开 PowerShell，执行：

```powershell
python --version
```

项目脚本会优先尝试使用：

```text
C:\Users\ASUS\AppData\Local\Programs\Python\Python310\python.exe
```

如果该路径不存在，会回退到系统 `python.exe`。

当前项目没有 `requirements.txt`、`pyproject.toml` 或 `package.json`，后端服务主体使用 Python 标准库。只启动页面、行为埋点、数据分析和商家看板时，不需要安装额外 npm 或 pip 依赖。

### 2.2 进入项目根目录

```powershell
cd F:\project\meituan
```

所有后续命令都建议在项目根目录执行。

## 3. 配置 AI 试戴环境变量

如果只启动页面、埋点和商家看板，可以跳过本节。

如果需要调用 AI 美甲试戴接口 `/api/tryon`，必须先配置 Ark / Seedream 相关环境变量。请在启动后端服务之前，在同一个 PowerShell 窗口执行：

```powershell
$env:ARK_API_KEY="替换为你的 Ark API Key"
$env:SEEDREAM_API_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"
$env:SEEDREAM_MODEL="doubao-seedream-4-0-250828"
$env:SEEDREAM_SIZE="1K"
$env:SEEDREAM_TIMEOUT_SECONDS="75"
$env:SEEDREAM_MAX_RETRIES="2"
$env:SEEDREAM_USE_STYLE_DETAIL_REF="true"
$env:SEEDREAM_WATERMARK="false"
```

注意事项：

- 不要把真实 `ARK_API_KEY` 写入代码、文档或提交到仓库。
- `SEEDREAM_SIZE=1K` 更适合本地快速验证。
- 如果希望生成更高清的展示图，可以临时改为 `2K`，但接口响应会更慢。
- 如果 AI 接口经常超时，可以把 `SEEDREAM_TIMEOUT_SECONDS` 调整为 `120`。
- 数据分析、商家看板、策略推荐等本地规则链路不依赖 `ARK_API_KEY`。

## 4. 推荐启动方式

在项目根目录执行：

```powershell
.\scripts\start_user_app.ps1
```

脚本会做这些事情：

- 检查默认端口 `8000` 是否已经被监听。
- 如果端口未占用，则后台启动 `python backend\server.py`。
- 将后端标准输出写入 `backend\server.out.log`。
- 将后端错误日志写入 `backend\server.err.log`。
- 将进程 PID 写入 `backend\server.pid`。

启动成功时，终端会输出类似：

```text
Started: http://127.0.0.1:8000/frontend/user-app.html
PID: 12345
```

如果端口已经有服务监听，脚本会输出类似：

```text
Server already listening: http://127.0.0.1:8000/frontend/user-app.html
PID: 12345
```

这通常表示服务已经启动，可以直接进入页面验证。

## 5. 可选：前台启动方式

如果你想直接在当前 PowerShell 窗口查看后端输出，可以执行：

```powershell
python backend\server.py
```

前台启动成功后会显示类似：

```text
Serving on http://127.0.0.1:8000/frontend/index.html
Event log: F:\project\meituan\backend\data\click_events.jsonl
```

前台启动时不要关闭该 PowerShell 窗口；关闭窗口会终止服务。

## 6. 健康检查

服务启动后，执行：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/health |
  Select-Object -ExpandProperty Content
```

返回内容中应包含：

```json
"ok": true
```

健康检查接口会列出当前后端可用的主要接口，包括：

- `/api/events`
- `/api/tryon`
- `/api/data-agent/run`
- `/api/data-agent/summary`
- `/api/merchant-ops/records`
- `/api/merchant-ops/summary`
- `/api/ops/merchant-dashboard`
- `/api/ops/platform-trends`
- `/api/ops/strategy/run`
- `/api/ops/strategy/explain`
- `/api/ops/strategy/accept`
- `/api/ops/campaign/generate`
- `/api/assistant/message`
- `/api/assistant/capabilities`
- `/api/ops/demo-data`

## 7. 页面访问

启动成功后，在浏览器打开：

```text
http://127.0.0.1:8000/frontend/index.html
```

也可以直接打开具体角色页面：

```text
http://127.0.0.1:8000/frontend/user-app.html
http://127.0.0.1:8000/frontend/merchant-dashboard.html
```

用户端用于上传手部图片、选择美甲款式、生成试戴预览和记录用户行为事件。

商家端用于查看运营数据、趋势、策略推荐和活动文案等能力。

## 8. 基础功能验证

### 8.1 验证演示运营数据

先生成演示数据：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/ops/demo-data `
  -Method POST |
  Select-Object -ExpandProperty Content
```

再运行数据分析：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/data-agent/run `
  -Method POST |
  Select-Object -ExpandProperty Content
```

读取数据分析摘要：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri http://127.0.0.1:8000/api/data-agent/summary |
  Select-Object -ExpandProperty Content
```

### 8.2 验证商家看板接口

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/api/ops/merchant-dashboard?merchantId=merchant_001&windowDays=7" |
  Select-Object -ExpandProperty Content
```

验证平台趋势接口：

```powershell
Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "http://127.0.0.1:8000/api/ops/platform-trends?windowDays=7" |
  Select-Object -ExpandProperty Content
```

### 8.3 验证策略推荐接口

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

成功返回时，内容中通常会包含 `recommendations`、`strategyType`、`title`、`reason`、`confidence` 等字段。

### 8.4 验证 AI 试戴链路

确认已经配置 `ARK_API_KEY` 后，可以通过用户端页面验证：

1. 打开 `http://127.0.0.1:8000/frontend/user-app.html`。
2. 上传一张真实手部图片。
3. 选择一个美甲款式。
4. 等待页面生成 AI 试戴结果。

如果没有配置 `ARK_API_KEY`，AI 试戴接口会返回 `seedream_not_configured`，页面可能退回到本地 Canvas 预览。

## 9. 查看日志和输出文件

后台脚本启动后，可以查看服务日志：

```powershell
Get-Content backend\server.out.log -Tail 80
Get-Content backend\server.err.log -Tail 80
```

查看行为埋点日志：

```powershell
Get-Content backend\data\click_events.jsonl -Tail 20
```

查看 AI 试戴任务日志：

```powershell
Get-Content backend\data\tryon_tasks.jsonl -Tail 20
```

查看数据分析产物：

```powershell
Get-ChildItem backend\data\structured_click_*
```

常见产物包括：

- `backend\data\structured_click_features.jsonl`
- `backend\data\structured_click_summary.json`

## 10. 停止服务

如果通过 `scripts\start_user_app.ps1` 后台启动，可以先读取 PID：

```powershell
Get-Content backend\server.pid
```

然后停止对应进程：

```powershell
Stop-Process -Id (Get-Content backend\server.pid)
```

也可以查看 8000 端口监听进程：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Where-Object { $_.State -eq "Listen" }
```

确认是本项目服务后，再停止对应 PID：

```powershell
Stop-Process -Id <PID>
```

## 11. 常见问题

### 11.1 端口 8000 被占用

检查监听进程：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Where-Object { $_.State -eq "Listen" }
```

如果是旧的本项目服务，可以停止旧进程后重新启动。

### 11.2 健康检查失败

优先检查：

- 是否已经在项目根目录执行启动命令。
- `backend\server.py` 是否正常运行。
- `backend\server.err.log` 是否有异常。
- 端口 `8000` 是否被其他程序占用。

### 11.3 AI 试戴返回 `seedream_not_configured`

说明启动后端服务前没有配置 `ARK_API_KEY`。在 PowerShell 中重新设置环境变量后，需要重启后端服务：

```powershell
$env:ARK_API_KEY="替换为你的 Ark API Key"
.\scripts\start_user_app.ps1
```

如果旧服务仍在运行，需要先停止旧进程，再重新启动。

### 11.4 AI 试戴返回 `seedream_request_failed`

优先检查：

- `ARK_API_KEY` 是否有效。
- 当前网络是否可以访问 Ark / Seedream 服务。
- `SEEDREAM_API_URL` 是否正确。
- `SEEDREAM_MODEL` 是否与 Ark 控制台开通的模型一致。
- 图片 URL 是否可被 Seedream 服务访问。

同时查看后端错误日志：

```powershell
Get-Content backend\server.err.log -Tail 80
```

### 11.5 商家看板没有数据

先生成演示数据，再运行数据分析：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/ops/demo-data -Method POST
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/data-agent/run -Method POST
```

然后刷新：

```text
http://127.0.0.1:8000/frontend/merchant-dashboard.html
```

## 12. 一次性启动和验证清单

按顺序执行：

```powershell
cd F:\project\meituan

# 如果需要 AI 试戴，先配置 Key；不需要 AI 试戴可以跳过这一段。
$env:ARK_API_KEY="替换为你的 Ark API Key"
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

最后打开：

```text
http://127.0.0.1:8000/frontend/index.html
http://127.0.0.1:8000/frontend/user-app.html
http://127.0.0.1:8000/frontend/merchant-dashboard.html
```
