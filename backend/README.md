# 后端服务目录

用于存放业务接口服务，包括用户、商户、款式、试戴任务、行为埋点、运营策略和数据看板接口。

## 当前本地服务

启动：

```powershell
python backend\server.py
```

接口：

- `POST /api/events`：记录上传、点击、预览等用户事件。
- `POST /api/tryon`：调用 Seedream 4.0/Ark 生成 AI 美甲试戴图。

Seedream 配置见：

- `backend/.env.example`
- `docs/seedream-tryon-integration.md`
