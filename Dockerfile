# ---------- 1. builder: сборка зависимостей ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


# ---------- 2. base: общая основа для test и runtime ----------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

# Безопасность: запуск от непривилегированного пользователя app
RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv

# Копируем исходный код приложения
COPY --chown=app:app alembic.ini .
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app app ./app
COPY --chown=app:app data ./data

# Гарантируем права на запись в папку сгенерированных документов
RUN mkdir -p data/generated data/templates && chown -R app:app /app


# ---------- 3. test: образ для прогона тестов в контейнере ----------
FROM base AS test

ENV PYTEST_ADDOPTS="-p no:cacheprovider"

COPY --chown=app:app requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY --chown=app:app pytest.ini .
COPY --chown=app:app tests ./tests

USER app
CMD ["pytest", "-v"]


# ---------- 4. runtime: финальный рабочий образ ----------
FROM base AS runtime

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/').getcode() == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]