#!/usr/bin/env bash
set -eu

# Das Basis-Image legt Tizen-Daten (Profile) unter /home/developer ab.
export HOME=/home/developer

echo "[addon] TheBoringJelly2SamsungPusher startet. Bedienung über die Seitenleiste (TheBoringJelly2SamsungPusher)."
PY=python3; [ -x /usr/bin/python3 ] && PY=/usr/bin/python3
echo "[addon] Python: $("$PY" --version 2>&1)"
exec "$PY" -I /app/server.py
