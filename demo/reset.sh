#!/usr/bin/env bash
set -e
WORK=${GRIDSHIFT_DEMO_WORK:-E:/demos/gridshift}
TOOLS=${DEV_TOOLS:-E:/dev-tools}
PY=$TOOLS/venv/Scripts/python
cd "$WORK/app"
powershell -NoProfile -Command "foreach (\$p in 8100,1125) { Get-NetTCPConnection -LocalPort \$p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force } }" || true
sleep 1
rm -rf data/demo.db data/demo.db-wal data/demo.db-shm data/mail
mkdir -p "$WORK/tmp"
export TEMP=$WORK/tmp TMP=$WORK/tmp PYTHONIOENCODING=utf-8 PLAYWRIGHT_BROWSERS_PATH=$TOOLS/browsers HF_HOME=$TOOLS/hf
nohup "$PY" -m scripts.mail_catcher --port 1125 --folder data/mail > "$WORK/mail.log" 2>&1 &
nohup "$PY" -m uvicorn backend.api.main:app --port 8100 > "$WORK/server.log" 2>&1 &
for i in $(seq 1 30); do curl -s 127.0.0.1:8100/api/health >/dev/null && break; sleep 1; done
curl -s 127.0.0.1:8100/api/auth/setup; echo
