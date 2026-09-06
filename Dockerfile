FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/home/chrome DISPLAY=:99
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium xvfb x11vnc fluxbox novnc websockify fonts-liberation fonts-noto-color-emoji ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m -d /home/chrome -s /bin/bash chromeuser && \
    mkdir -p /app/storage/chrome-profile /app/storage/debug /home/chrome/.vnc && \
    chown -R chromeuser:chromeuser /app/storage /home/chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV NOVNC_PORT=6080
EXPOSE 10000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["sh","-c","rm -f /tmp/.X99-lock; \
Xvfb :99 -screen 0 1365x900x24 -ac -nolisten tcp >/app/storage/debug/xvfb.log 2>&1 & \
for i in $(seq 1 30); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 1; done; \
su -s /bin/sh chromeuser -c 'fluxbox >/app/storage/debug/fluxbox.log 2>&1 & chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1365,900 --no-first-run --no-default-browser-check --disable-notifications --user-data-dir=/app/storage/chrome-profile about:blank >/app/storage/debug/chrome.log 2>&1 &'; \
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw >/app/storage/debug/x11vnc.log 2>&1 & \
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/app/storage/debug/novnc.log 2>&1 & \
gunicorn app:app --bind 0.0.0.0:10001 --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - & nginx -c /app/nginx.conf -g 'daemon off;'"]
