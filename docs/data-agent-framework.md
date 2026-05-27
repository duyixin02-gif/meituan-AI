# 数据处理 Agent 框架

本框架用于把试戴前端产生的点击事件整理成可分析的结构化行为数据，并先以自然语言标签形式保存，作为后续统计分析、用户偏好建模和商家运营洞察的基础。

## 当前输入

- `backend/data/click_events.jsonl`
- 主要处理事件：
  - `style_click`
  - `local_preview_generated`
  - `ai_tryon_completed`
  - `ai_tryon_failed`

当前项目还没有接入正式数据库，因此先把 JSONL 事件日志视为本地事件仓库。后续可以用数据库 repository 替换 `JsonlEventRepository`。

## Agent 分层

- `ClickEventCleanerAgent`：清洗点击事件，提取会话、款式、事件类型、时间、图片路径和来源 URL。
- `StyleFeatureAgent`：将点击行为拆成自然语言特征，包括视觉基础标签、甲型与结构标签、用户侧场景与人群标签。
- `FeatureStore`：将自然语言特征写入 JSONL，并保存统计摘要。
- `DataAgentOrchestrator`：编排完整流程，负责读取、清洗、特征拆解、去重存储和摘要生成。

## 当前输出

- `backend/data/structured_click_features.jsonl`
  - 逐条保存自然语言行为记录和三类标签。
- `backend/data/structured_click_summary.json`
  - 保存事件类型、热门款式、标签计数、款式画像等统计摘要。
- `backend/data/merchant_ops_test_records.jsonl`
  - 保存后续商家自动化运营系统的测试数据，适合存放约 200 条本地样本。

## API

启动后端：

```powershell
python backend\server.py
```

触发一次数据处理：

```http
POST http://127.0.0.1:8000/api/data-agent/run
```

读取最近摘要：

```http
GET http://127.0.0.1:8000/api/data-agent/summary
```

写入商家运营测试数据：

```http
POST http://127.0.0.1:8000/api/merchant-ops/records
```

单条写入示例：

```json
{
  "merchantId": "merchant_001",
  "eventType": "campaign_candidate",
  "styleId": "style_001",
  "userSegment": "通勤白领",
  "scenarioTags": ["工作日", "低调精致"],
  "styleTags": ["裸色", "短甲", "通勤"],
  "metrics": {
    "clickCount": 12,
    "tryonCount": 5
  },
  "notes": "可用于测试商家自动化推荐策略"
}
```

批量写入时传入 `records` 数组即可：

```json
{
  "records": [
    {
      "merchantId": "merchant_001",
      "eventType": "campaign_candidate",
      "styleId": "style_001"
    },
    {
      "merchantId": "merchant_001",
      "eventType": "campaign_candidate",
      "styleId": "style_002"
    }
  ]
}
```

读取商家运营测试数据：

```http
GET http://127.0.0.1:8000/api/merchant-ops/records?limit=200
```

读取商家运营测试数据摘要：

```http
GET http://127.0.0.1:8000/api/merchant-ops/summary
```

生成一批演示数据：

```http
POST http://127.0.0.1:8000/api/ops/demo-data
```

商家后台页面：

```http
GET http://127.0.0.1:8000/frontend/merchant-dashboard.html
```

读取单个商家的后台摘要：

```http
GET http://127.0.0.1:8000/api/ops/merchant-dashboard?merchantId=merchant_001&windowDays=7
```

读取平台匿名趋势：

```http
GET http://127.0.0.1:8000/api/ops/platform-trends?windowDays=7
```

生成自动运营策略：

```http
POST http://127.0.0.1:8000/api/ops/strategy/run
```

请求体：

```json
{
  "merchantId": "merchant_001",
  "windowDays": 7
}
```

策略生成目前使用本地规则引擎，`backend/ops_agent.py` 中的 `OpenClawStrategyAdapter` 已接入 OpenClaw 网关配置位；OpenClaw 负责多渠道唤起、自然语言解释和商家个性化追问，本地规则继续负责排序、安全审查和隐私边界。详见 `docs/openclaw-strategy-assistant.md`。

多办公工具统一助手入口：

```http
POST http://127.0.0.1:8000/api/assistant/message
```

该入口使用 `office-assistant-v1` 协议，把飞书、Slack、Teams、钉钉、企业微信等渠道消息统一成策略生成、解释、活动文案、采纳记录和复盘提醒等能力。详见 `docs/office-assistant-gateway.md`。

健康检查会列出数据处理接口：

```http
GET http://127.0.0.1:8000/api/health
```

## 后续扩展

- 将 `JsonlEventRepository` 替换为数据库读取层。
- 将 `StyleFeatureAgent` 的规则标签替换或增强为多模态模型识别结果。
- 增加人工标注回流，把自然语言标签沉淀为枚举标签体系。
- 增加统计分析任务，例如款式热度、试戴转化、用户偏好聚类、场景人群画像。
- 基于 `merchant_ops_test_records.jsonl` 生成商家自动化运营策略测试集。
