# 多办公工具策略助手网关

本项目新增 `office-assistant-v1` 协议，用于让 OpenClaw、飞书、Slack、Teams、钉钉、企业微信、邮件等办公工具通过同一套后端接口调用项目能力。

## 架构定位

```text
飞书 / Slack / Teams / 钉钉 / 企业微信 / 邮件
        ↓
OpenClaw 或渠道适配器
        ↓
POST /api/assistant/message
        ↓
策略生成 / 策略解释 / 活动文案 / 采纳记录 / 复盘提醒
```

OpenClaw 负责多渠道消息接入和对话编排；本项目后端负责商家数据分析、策略生成、安全边界和动作审计。

## 统一入口

```http
POST http://127.0.0.1:8000/api/assistant/message
```

请求示例：

```json
{
  "channel": "feishu",
  "externalUserId": "ou_xxx",
  "merchantId": "merchant_001",
  "intent": "generate_strategy",
  "message": "帮我看看今天主推哪款",
  "locale": "zh-CN",
  "windowDays": 7,
  "conversationId": "chat_xxx",
  "context": {
    "source": "openclaw",
    "merchantId": "merchant_001"
  }
}
```

如果 `intent` 为空，后端会根据 `message` 做轻量意图识别。

## 支持的意图

- `generate_strategy`：生成自动策略建议。
- `clean_data`：清洗原始点击/试戴事件，生成结构化特征和数据摘要。
- `explain_strategy`：解释某条策略为什么成立。
- `generate_campaign`：把策略转成活动方案和文案。
- `accept_strategy`：记录商家采纳动作。
- `create_follow_up`：创建复盘提醒记录。
- `show_capabilities`：返回助手能力说明。

也可以直接调用细分接口：

```http
POST /api/ops/strategy/explain
POST /api/ops/campaign/generate
POST /api/ops/strategy/accept
GET  /api/assistant/capabilities
```

## 响应格式

```json
{
  "ok": true,
  "protocol": "office-assistant-v1",
  "intent": "generate_strategy",
  "channel": "feishu",
  "merchantId": "merchant_001",
  "reply": {
    "text": "建议主推 style_007...",
    "cards": [
      {
        "type": "strategy",
        "title": "设置试戴页主推款式",
        "fields": [
          { "label": "置信度", "value": "high" }
        ],
        "explanation": "这条建议由规则排序，并由 OpenClaw 助手层补充解释。"
      }
    ],
    "actions": [
      {
        "type": "confirm",
        "label": "采纳策略",
        "intent": "accept_strategy"
      }
    ]
  },
  "data": {},
  "audit": {
    "generatedAt": "2026-05-25T00:00:00+00:00",
    "externalUserId": "ou_xxx",
    "requiresMerchantMapping": false
  }
}
```

办公工具适配器可以把 `reply.text` 转成普通文本，把 `reply.cards` 转成飞书/Slack/Teams 卡片，把 `reply.actions` 转成按钮或确认交互。

## 安全边界

- `channel + externalUserId` 应在正式环境中映射到唯一商家、角色和权限。
- 未完成身份映射时，响应中的 `audit.requiresMerchantMapping` 会提醒调用方补齐权限层。
- 高影响动作使用 `reply.actions[].type = confirm`，渠道侧应让商家确认后再调用 `accept_strategy`。
- 平台趋势只使用满足隐私阈值的聚合数据。
- 动作审计写入 `backend/data/office_assistant_actions.jsonl`。

## OpenClaw 接入方式

OpenClaw 的任意渠道入口只需要把消息标准化为上面的请求体，再调用：

```http
POST /api/assistant/message
```

推荐把不同渠道保留在 `channel` 字段中，例如：

- `feishu`
- `slack`
- `teams`
- `dingtalk`
- `wecom`
- `email`

这样核心策略逻辑不需要为每个办公工具重复实现。
