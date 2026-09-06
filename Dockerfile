FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp DISPLAY=:99
RUN apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver xvfb fonts-liberation fonts-noto-color-emoji ca-certificates tini procps && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/storage/whatsapp_session /app/storage/debug && chmod -R 777 /app/storage
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["sh","-c","rm -f /tmp/.X99-lock; Xvfb :99 -screen 0 1365x900x24 -ac -nolisten tcp >/app/storage/debug/xvfb.log 2>&1 & for i in $(seq 1 30); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 1; done; exec gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 180 --access-logfile - --error-logfile -"]
