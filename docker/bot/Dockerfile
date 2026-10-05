FROM python:3.12-slim AS production

# ffmpeg из подписанного репозитория Debian, а не архив со стороннего сайта
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash -s -- -i /usr/local -n

# Бот работает не от root. Ключ сервисного аккаунта Yandex Cloud в образ не кладётся:
# docker-compose монтирует yc_config.yaml в ~/.config/yandex-cloud/config.yaml при запуске
RUN useradd --create-home --uid 1000 app && \
    mkdir -p /home/app/.config/yandex-cloud /app/var/log && \
    chown -R app:app /home/app/.config /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Что не попадает в образ (секреты, тесты, .git) — в .dockerignore
COPY --chown=app:app . .

USER app
CMD ["python", "main.py"]
