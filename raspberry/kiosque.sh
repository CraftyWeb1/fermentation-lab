#!/bin/bash
# Plein ecran sur l ecran du Raspberry Pi (tactile HDMI ou DSI 7").
# Lancer app.py d abord, ou ce script si tu veux les deux.

cd "$(dirname "$0")"
export FERMIA_KIOSQUE=1
python3 app.py &
sleep 4
chromium-browser --kiosk --noerrdialogs --disable-infobars \
  --check-for-update-interval=31536000 \
  "http://127.0.0.1:8765" || \
chromium --kiosk --noerrdialogs --disable-infobars \
  "http://127.0.0.1:8765"
