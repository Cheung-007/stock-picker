#!/bin/bash
# 生成可双击的 macOS 桌面应用（.app 包）
# 双击后：启动后端 + 打开浏览器看板；再次双击可停止。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="超短选股"
APP_DIR="$HOME/Desktop/$APP_NAME.app"

echo ">>> 项目目录: $PROJECT"
echo ">>> 生成应用: $APP_DIR"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

# 1) Info.plist
cat > "$APP_DIR/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>superselect</string>
  <key>CFBundleDisplayName</key><string>超短选股</string>
  <key>CFBundleIdentifier</key><string>com.cheung.superselect</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# 2) launcher 启动脚本（__PROJECT__ 占位符稍后替换为实际绝对路径）
cat > "$APP_DIR/Contents/MacOS/launcher" <<'LAUNCHER'
#!/bin/bash
# T+1 超短线选股系统 启动器
PROJECT="__PROJECT__"
PID_FILE="$PROJECT/.run/backend.pid"
LOG_FILE="$PROJECT/.run/backend.log"
PORT=8000
URL="http://127.0.0.1:$PORT"

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

start_backend() {
  cd "$PROJECT" || exit 1
  mkdir -p .run

  # 首次运行：准备后端环境
  if [ ! -d ".venv" ]; then
    osascript -e 'display dialog "首次运行，正在安装后端依赖（约 1 分钟）…" buttons {"好"} default button "好" with title "超短选股"' &
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -q
  fi
  # 前端依赖/构建（若缺失）
  if [ ! -d "frontend/node_modules" ]; then
    (cd frontend && npm install)
  fi
  if [ ! -d "frontend/dist" ]; then
    (cd frontend && npm run build)
  fi

  nohup .venv/bin/uvicorn backend.api.main:app --host 127.0.0.1 --port $PORT > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"

  # 等待后端端口就绪（静态页立即返回 200）
  for _ in $(seq 1 60); do
    if curl -s -o /dev/null "$URL/" 2>/dev/null; then break; fi
    sleep 0.5
  done
}

stop_backend() {
  if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  pkill -f "backend.api.main:app" 2>/dev/null || true
  sleep 0.5
}

if is_running; then
  choice="$(osascript <<'EOF'
set c to button returned of (display dialog "超短选股系统已在后台运行。" buttons {"打开看板", "停止系统", "取消"} default button "打开看板" with title "T+1 超短线选股系统")
return c
EOF
)"
  case "$choice" in
    "打开看板") open "$URL" ;;
    "停止系统") stop_backend ;;
  esac
else
  start_backend
  open "$URL"
fi
LAUNCHER

# 替换项目路径占位符
sed -i '' "s|__PROJECT__|$PROJECT|g" "$APP_DIR/Contents/MacOS/launcher"

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# 3) 图标
if [ -f "$SCRIPT_DIR/AppIcon.icns" ]; then
  cp "$SCRIPT_DIR/AppIcon.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
fi

# 4) 清除可能的隔离属性（本地生成，一般无；确保可双击）
xattr -dr com.apple.quarantine "$APP_DIR" 2>/dev/null || true

echo ">>> 完成。桌面图标：$APP_DIR"
echo ">>> 双击即可启动；再次双击可停止或打开看板。"
