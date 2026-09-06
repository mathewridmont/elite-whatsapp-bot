FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 DISPLAY=:99 HOME=/home/chrome
RUN apt-get update && apt-get install -y --no-install-recommends chromium xvfb x11vnc fluxbox novnc fonts-liberation fonts-noto-color-emoji ca-certificates tini && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m -d /home/chrome -s /bin/bash chromeuser && mkdir -p /app/storage/chrome-profile /app/storage/debug && chown -R chromeuser:chromeuser /app/storage /home/chrome
EXPOSE 10000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["sh","-c","rm -f /tmp/.X99-lock; Xvfb :99 -screen 0 1365x900x24 -ac -nolisten tcp >/app/storage/debug/xvfb.log 2>&1 & for i in $(seq 1 30); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 1; done; su -s /bin/sh chromeuser -c 'fluxbox >/app/storage/debug/fluxbox.log 2>&1 & chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1365,900 --no-first-run --no-default-browser-check --disable-notifications --user-data-dir=/app/storage/chrome-profile about:blank >/app/storage/debug/chrome.log 2>&1 &' ; exec python server.py"]
