# OpenClaw 自动策略助手接入说明

本项目将 OpenClaw 定位为“多渠道、自然语言、可解释性”的策略助手网关，而不是替代本地规则策略引擎。

如果需要让飞书、Slack、Teams、钉钉、企业微信等办公工具共用同一套项目能力，优先使用 `POST /api/assistant/message` 统一入口。详见 `docs/office-assistant-gateway.md`。

## 分工

- 本地规则引擎：负责商家数据聚合、款式/标签排序、策略动作生成、安全审查和隐私边界。
- OpenClaw：负责把规则策略解释成商家能理解的自然语言，并支持从外部渠道继续追问、生成活动文案或跟进观察计划。
- 本地兜底解释：当 OpenClaw 未配置或调用失败时，接口仍返回可解释策略，保证演示和本地开发稳定。

## 后端入口

策略接口仍为：

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

响应中新增：

- `assistant.summary`：策略助手摘要。
- `assistant.handoff`：OpenClaw 多渠道交接信息，包含渠道、商家和可继续处理的意图。
- `recommendations[].assistantExplanation`：每条策略的自然语言解释。
- `recommendations[].merchantPersonalization`：面向商家的个性化追问和提示词。
- `recommendations[].explainability`：决策输入和安全边界说明。
- `ai`：OpenClaw 配置状态。

## 环境变量

未配置时使用本地解释模式。

```powershell
$env:OPENCLAW_STRATEGY_WEBHOOK_URL="https://your-openclaw-gateway.example.com/strategy"
$env:OPENCLAW_STRATEGY_CHANNEL="merchant-dashboard"
$env:OPENCLAW_STRATEGY_TIMEOUT="4"
python backend\server.py
```

OpenClaw webhook 需要接收一个 JSON 对象，字段包括：

- `task`: 固定为 `merchant_strategy_assistant`
- `channel`: 当前渠道
- `merchantId`
- `windowDays`
- `rulesOutput`: 本地规则生成的策略
- `dashboard`: 已压缩的商家经营摘要
- `platformTrends`: 已压缩且满足隐私阈值的平台趋势
- `requirements`: 输出要求

建议 OpenClaw 返回：

```json
{
  "summary": "本次建议优先主推 style_007，并围绕红色标签做短周期活动。",
  "recommendations": [
    {
      "strategyType": "featured_style",
      "assistantExplanation": "这款式点击和试戴率同时较高，适合作为 3 天主推。",
      "merchantPersonalization": {
        "followUpQuestion": "要不要把它转成活动文案或观察计划？"
      }
    }
  ],
  "source": "OpenClaw"
}
```

## 安全原则

- OpenClaw 只增强解释和渠道编排，不直接绕过本地策略排序。
- 不向 OpenClaw 传递其他商家的原始明细。
- 平台趋势只传递满足隐私阈值后的聚合结果。
- 最终返回仍经过 `SafetyReviewAgent` 的策略安全审查。
