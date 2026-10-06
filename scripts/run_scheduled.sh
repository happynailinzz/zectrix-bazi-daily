#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON="${ZECTRIX_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
OUTPUT="${ZECTRIX_OUTPUT:-/tmp/zectrix-bazi-daily.png}"
LOG="/var/log/zectrix-bazi-daily.log"
LOCK="/tmp/zectrix-bazi-daily.lock"
MAX_LOG_BYTES=1048576

export TZ="${ZECTRIX_TIMEZONE:-Asia/Shanghai}"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python 环境未找到：$PYTHON" >&2
    exit 1
fi

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# 日志轮转（截断到最近 1MB）
if [ -f "$LOG" ]; then
    size=$(wc -c < "$LOG" 2>/dev/null || echo 0)
    if [ "$size" -gt "$MAX_LOG_BYTES" ]; then
        tail -c 262144 "$LOG" > "$LOG.tmp" && cat "$LOG.tmp" > "$LOG" && rm -f "$LOG.tmp"
    fi
fi

# 并发保护
exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date '+%F %T') SKIP: 上一次运行未完成" >> "$LOG"
    exit 0
fi

cd "$PROJECT_DIR"
echo "$(date '+%F %T') START daily push page=4" >> "$LOG"
"$PYTHON" scripts/make_display.py --out "$OUTPUT" --push --page 4 >> "$LOG" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    echo "$(date '+%F %T') OK" >> "$LOG"
else
    echo "$(date '+%F %T') FAILED rc=$rc" >> "$LOG"
fi
exit $rc
