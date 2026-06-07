# 前端应用目录

用于存放用户端和商户端前端应用。

用户端重点：

- 上传手图
- 选择款式
- 查看试戴效果
- 收藏、分享、预约、下单

商户端重点：

- 热款排行
- 趋势曲线
- 运营建议
- 活动文案生成

## 本地页面入口

当前前端已按角色拆分：

- `index.html`
- `user-app.html`
- `styles.css`
- `app.js`
- `merchant-dashboard.html`
- `merchant-dashboard.css`
- `merchant-dashboard.js`
- `assets/catalog.js`

直接用浏览器打开 `frontend/index.html` 会看到两个独立入口链接。

用户端可直接打开 `frontend/user-app.html` 使用试戴功能。商家端需要先打开 `frontend/merchant-login.html` 登录，再进入 `frontend/merchant-dashboard.html`。

用户端当前能力：

- 上传手部照片。
- 右侧滑动浏览可试戴款式。
- 点击款式生成融合预览。
- 点击、上传、预览生成事件会优先尝试发送到 `/api/events`。
- 如果没有后端服务，事件会保存在浏览器 `localStorage`。
- 点击“导出记录”可以导出本地事件 JSON。
