FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright (Firefox)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    libgtk-3-0 libdbus-glib-1-2 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 libasound2 libpangocairo-1.0-0 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libnspr4 libnss3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install firefox

COPY app/ app/

EXPOSE 8765

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
