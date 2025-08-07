# Dockerfile для Rage Restart Bot
# Упрощённая сборка для надёжности (временно, до решения проблемы с зависимостями)

FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    # Для работы с Docker
    curl \
    # Для мониторинга сети
    netcat-traditional \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для запуска приложения (безопасность)
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Устанавливаем pip зависимости
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip list | grep docker

# Метаданные образа
LABEL maintainer="rage-bot-team" \
      version="1.0" \
      description="Telegram bot for managing Rage server in Docker"

# Рабочая директория
WORKDIR /app

# Копируем исходный код
COPY src/ /app/src/
COPY config/ /app/config/

# Создаем директории для логов и данных
RUN mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Переменные окружения
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Том для логов
VOLUME ["/app/logs"]

# Том для конфигурации (для монтирования извне)
VOLUME ["/app/config"]

# Health check для контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app'); from src.utils.config import config_manager; config_manager.get_telegram_token()" || exit 1

# Точка входа
CMD ["python", "src/main.py"]