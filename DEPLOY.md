# 部署说明

## 一、本地启动（无需 AI / 无需 Node，双击即用）

双击 `启动系统.command`（或终端执行 `./start.sh`）。

首次运行会自动：创建虚拟环境 → 装依赖 → 构建前端（仅首次需 Node）→ 启动服务并打开浏览器。

访问地址：http://127.0.0.1:8000

> 系统为纯 Python 规则引擎（抓数 → 指标计算 → 信号分级 → 买卖建议），
> 运行时不调用任何 AI/LLM（DeepSeek/Claude 等），脱离 AI 助手可独立运行。

---

## 二、线上部署（Render 免费托管）

Render 免费层：自带 `https://xxx.onrender.com` 子域名 + HTTPS，无需域名与备案。

### 步骤

1. **推送到 GitHub**（需 GitHub 账号）
   ```bash
   cd /Users/cheung/Cheung/AI/cc
   git init
   git add .
   git commit -m "stock picker"
   # 在 GitHub 新建空仓库 stock-picker 后：
   git remote add origin git@github.com:<你的用户名>/stock-picker.git
   git push -u origin main
   ```

2. **在 Render 创建服务**
   - 打开 https://render.com 用 GitHub 登录
   - `New` → `Blueprint` → 选择刚推送的仓库
   - Render 自动识别根目录的 `render.yaml` 与 `Dockerfile`，点击 `Apply` 部署

3. **获取访问地址**
   - 部署完成后，服务详情页显示 `https://stock-picker-xxxx.onrender.com`
   - 手机（iOS Safari / 安卓原生 / 微信内置浏览器）直接打开该地址即可

---

## 三、免费层注意事项

- **冷启动**：免费实例 15 分钟无访问会休眠，下次打开需等待约 30–60 秒（含数据抓取）。
  介意可升级 Starter（约 $7/月）保持常驻。
- **数据源**：行情来自东方财富/腾讯/新浪公开接口。海外机房直连通常可用；
  历史 K 线、历史资金流已内置腾讯/新浪备用源自动兜底。
- **时区**：容器已装 `tzdata`，调度器按 Asia/Shanghai 交易日盘中每 5 分钟刷新。

---

## 四、故障排查

| 现象 | 原因与处理 |
|---|---|
| 主看板数据为空 | 海外机房访问东财 push2 被限/慢，可在 `backend/config.py` 调整 `PUSH2_HOSTS` 顺序，或后续扩展腾讯/新浪为主源 |
| 首次打开很慢 | 免费层冷启动 + 首次全量抓数（约 1 分钟），属正常 |
| 手机表格看不清 | 已做响应式适配，可横向滑动查看完整列 |
