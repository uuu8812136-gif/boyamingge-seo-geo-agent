FROM python:3.11-slim

WORKDIR /app

COPY apt-retries.conf /etc/apt/apt.conf.d/80-retries

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 && \
    pip install --no-cache-dir -r requirements.txt

# 外部平台扫码登录与发布需要 Chromium；固定共享路径，非 root 用户也可运行。
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN set -eu; \
    for attempt in 1 2 3; do \
      if python -m playwright install --with-deps chromium; then break; fi; \
      if [ "$attempt" = "3" ]; then exit 1; fi; \
      echo "Playwright 安装失败，第 $attempt 次重试"; \
      sleep 5; \
    done; \
    chmod -R a+rX /ms-playwright

COPY . .

# 预创建上传目录并赋权
RUN mkdir -p /app/uploads /app/data/synapse_cookies && chmod 755 /app/uploads /app/data/synapse_cookies

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 非 root 用户运行
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
