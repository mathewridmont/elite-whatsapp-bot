FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver xvfb fonts-liberation fonts-noto-color-emoji ca-certificates tini procps && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/storage/whatsapp_session /app/storage/debug
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["sh","-c","Xvfb :99 -screen 0 1440x1000x24 -ac +extension RANDR >/tmp/xvfb.log 2>&1 & export DISPLAY=:99; gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 180 --access-logfile - --error-logfile -"]
