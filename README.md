# 美甲 AI 试戴与商家智能运营平台

本项目构建了一个面向用户和商家的美甲智能试戴与运营平台。用户可以上传手部图片并选择美甲款式进行 AI 试戴，商家可以基于用户点击、试戴、收藏和转化行为查看运营看板，并通过 OpenClaw 将策略生成、策略解释、活动文案和复盘提醒等能力接入飞书、Slack、Teams、钉钉、企业微信、邮件等办公工具。

项目重点关注三类能力：

- 用户侧美甲试戴平台：支持款式浏览、手图上传、AI 融图试戴、本地预览降级和行为埋点。
- 商家侧自动运营：基于试戴与点击数据生成款式表现、标签趋势、转化漏斗和运营策略建议。
- 多办公工具接入与数据安全：通过 OpenClaw 和统一后端协议接入多个办公软件，同时在后端完成商家数据隔离、聚合脱敏和动作审计。

## 核心功能

### 用户美甲试戴

- 支持用户上传手部照片，并选择可试戴美甲款式。
- 后端通过 `/api/tryon` 编排 Seedream / Ark 图像生成任务，将用户手图与款式图融合。
- Prompt 约束只修改可见指甲区域，尽量保持用户原图的手型、肤色、光照、背景、构图和手指数量不变。
- 前端会优先调用 AI 试戴接口；如果后端或模型服务不可用，会降级为本地 Canvas 预览。
- 通过 1K 输出、前端压缩手图和快速失败降级等方式优化响应链路，目标是将用户试戴响应控制在 1 分钟以内。

### 商家运营看板

- 记录用户点击、上传、试戴、收藏、预约意向等行为事件。
- 数据 Agent 将原始行为日志清洗为结构化特征和自然语言标签。
- 商家后台按 `merchant_id` 聚合数据，展示点击量、试戴量、收藏量、转化率、款式表现、标签热度和趋势变化。
- 平台趋势只展示满足隐私阈值后的聚合结果，避免暴露其他商家的原始数据。

### 自动策略生成

- 策略引擎根据款式热度、试戴率、点击增长、转化表现和平台趋势生成运营建议。
- 支持主推款推荐、标签活动方向、低转化款优化、数据不足提醒和复盘建议。
- 每条策略包含推荐理由、置信度、观察指标、风险提示和可执行动作。
- 策略结果会经过安全审查，避免直接输出越权数据或高风险运营建议。

### OpenClaw 多办公工具接入

项目提供统一的 `office-assistant-v1` 协议入口：

```http
POST /api/assistant/message
```

OpenClaw 或渠道适配器可以把不同办公工具中的消息标准化为同一套请求体，再调用后端能力：

- `generate_strategy`：生成自动策略建议。
- `clean_data`：清洗点击和试戴事件。
- `explain_strategy`：解释策略推荐原因。
- `generate_campaign`：生成活动方案和运营文案。
- `accept_strategy`：记录商家采纳动作。
- `create_follow_up`：创建复盘提醒。
- `show_capabilities`：返回助手能力说明。

OpenClaw 负责多渠道消息接入和自然语言编排；本项目后端负责商家数据分析、策略生成、安全边界、权限过滤和动作审计。这样核心运营能力可以自由接入飞书、Slack、Teams、钉钉、企业微信、邮件等办公软件，而不需要为每个渠道重复实现业务逻辑。

### 数据隔离与脱敏

- 商家端数据查询以 `merchant_id` 为核心隔离维度。
- 正式数据库设计中，商家登录态应由后端映射到唯一商家、角色和权限，不能信任前端随意传入的商家 ID。
- 平台趋势只暴露满足隐私阈值的聚合数据。
- 手机号等敏感信息建议保存哈希和脱敏展示值。
- OpenClaw 只接收经过压缩、聚合、权限过滤后的运营摘要和策略结果，不接收其他商家的原始明细。
- 高影响动作通过确认型 action 执行，并写入审计日志。

## 技术结构

```text
frontend/
  用户端试戴页面、商家登录页、商家运营看板

backend/
  HTTP 服务、AI 试戴编排、数据 Agent、策略引擎、OpenClaw 办公助手网关

data/
  原始图片资产、处理后款式目录、试戴配对数据和 schema

docs/
  Seedream 接入、OpenClaw 接入、办公助手协议、数据 Agent、MySQL 数据模型等说明

tests/
  策略引擎和办公助手网关测试
```

核心文件：

- `backend/server.py`：后端 HTTP 服务入口。
- `backend/tryon_service.py`：AI 美甲试戴任务编排。
- `backend/seedream_client.py`：Seedream / Ark 图像生成客户端。
- `backend/data_agent.py`：点击与试戴行为数据清洗。
- `backend/ops_agent.py`：商家看板聚合、策略生成、OpenClaw 策略适配和安全审查。
- `backend/assistant_gateway.py`：多办公工具统一助手协议入口。
- `frontend/user-app.html`：用户侧试戴页面。
- `frontend/merchant-dashboard.html`：商家运营看板。

## 主要接口

```http
GET  /api/health
POST /api/events
POST /api/tryon
POST /api/data-agent/run
GET  /api/data-agent/summary
GET  /api/ops/merchant-dashboard
GET  /api/ops/platform-trends
POST /api/ops/strategy/run
POST /api/ops/strategy/explain
POST /api/ops/campaign/generate
POST /api/ops/strategy/accept
POST /api/assistant/message
GET  /api/assistant/capabilities
```

## 本地启动

启动后端服务：

```powershell
python backend\server.py
```

打开前端入口：

```text
frontend/index.html
```

用户端页面：

```text
frontend/user-app.html
```

商家端页面：

```text
frontend/merchant-dashboard.html
```

如需调用真实 AI 试戴接口，需要配置 Ark / Seedream 相关环境变量：

```powershell
$env:ARK_API_KEY="your-api-key"
$env:SEEDREAM_MODEL="doubao-seedream-4-0-250828"
$env:SEEDREAM_SIZE="1K"
$env:SEEDREAM_TIMEOUT_SECONDS="75"
```

如需接入 OpenClaw 策略助手，可配置：

```powershell
$env:OPENCLAW_STRATEGY_WEBHOOK_URL="https://your-openclaw-gateway.example.com/strategy"
$env:OPENCLAW_STRATEGY_CHANNEL="merchant-dashboard"
$env:OPENCLAW_STRATEGY_TIMEOUT="4"
```

未配置 OpenClaw 时，后端会使用本地解释模式返回可解释策略，保证本地演示和开发稳定。

## 观测与审计

当前项目已经保留多类 JSONL 日志，便于追踪用户行为、AI 试戴任务、策略生成和办公助手动作：

```text
backend/data/click_events.jsonl
backend/data/tryon_tasks.jsonl
backend/data/merchant_strategy_recommendations.jsonl
backend/data/office_assistant_actions.jsonl
backend/data/structured_click_features.jsonl
backend/data/structured_click_summary.json
```

建议在后续生产化时增加统一的 AI / Skill 调用审计日志，例如：

```text
backend/data/ai_skill_invocations.jsonl
```

并用同一个 `traceId` 串联 `/api/assistant/message`、策略生成、OpenClaw webhook、Seedream 图像生成和最终响应，监控每个 skill 的调用次数、成功率、P95 延迟、超时次数、权限范围和隐私过滤情况。

## 文档

- `docs/seedream-tryon-integration.md`：Seedream 4.0 美甲试戴接入说明。
- `docs/openclaw-strategy-assistant.md`：OpenClaw 自动策略助手接入说明。
- `docs/office-assistant-gateway.md`：多办公工具策略助手网关协议。
- `docs/data-agent-framework.md`：数据处理 Agent 框架。
- `docs/mysql-data-model.md`：后续 MySQL 数据模型设计。
- `docs/project-startup-guide.md`：项目启动与验证指南。

## 当前状态

项目当前以本地文件和 JSONL 作为轻量数据仓库，已具备用户试戴、事件采集、数据清洗、商家运营看板、策略生成、办公助手协议和 OpenClaw 接入配置位。后续可以将底层 JSONL repository 替换为 MySQL 或其他正式数据库，并补充登录鉴权、对象存储、消息队列、统一监控和生产级权限系统。
