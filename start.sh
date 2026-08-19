#!/bin/bash
# 本地一键启动：单进程（FastAPI 托管前端构建产物），无需 Node/AI 依赖
# 用法：./start.sh  或双击 启动系统.command
set -e
cd "$(dirname "$0")"

# 后端虚拟环境（首次自动创建并安装依赖）
if [ ! -d ".venv" ]; then
  echo ">>> 首次运行：创建虚拟环境并安装依赖..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt -q
fi

# 前端构建产物（仅在缺失时构建，之后无需 Node）
if [ ! -f "frontend/dist/index.html" ]; then
  echo ">>> 首次运行：构建前端（需 Node，仅一次）..."
  (cd frontend && npm install && npm run build)
fi

echo ">>> 启动系统：http://127.0.0.1:8000"
.venv/bin/uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 &
PID=$!

# 自动打开浏览器
sleep 2
open http://127.0.0.1:8000 2>/dev/null || true

trap "kill $PID 2>/dev/null" INT TERM
wait
