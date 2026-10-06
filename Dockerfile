# ==========================================
# ЭТАП 1: Builder (Сборка зависимостей)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости, необходимые для компиляции пакетов (если понадобятся)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirments.txt .

# Устанавливаем зависимости в отдельную папку wheels / site-packages
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --prefix=/install -r requirments.txt

# ==========================================
# ЭТАП 2: Final Runtime Image (Легковесный образ)
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Для работы psycopg2 в runtime нужен только libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копируем только установленные библиотеки из этапа builder
COPY --from=builder /install /usr/local

# Копируем исходный код приложения
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]