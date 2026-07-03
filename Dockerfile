# WildAutomations — AI Sales Intelligence CRM (Railway/Docker)
# Python 3.12 pinned so the runtime is stable (no uv-managed-python drift).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Chromium + its OS libraries for the browser scrapers (Maps / Instagram /
# LinkedIn-via-Google). Version matches the installed playwright package.
RUN playwright install --with-deps chromium

# App source
COPY . .

# Railway injects $PORT at runtime; test_ui.py reads it (falls back to 8001).
ENV PORT=8001
EXPOSE 8001

# Health: GET / returns 200 (dashboard). Railway can use this as healthcheck path.
CMD ["python", "test_ui.py"]
