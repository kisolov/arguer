FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | \
    tar -xJ -C /usr/local/bin --strip-components=1 --wildcards '*/ffmpeg' '*/ffprobe' && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

RUN curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash -s -- -i /usr/local -n

COPY requirements.txt .

COPY yc_config.yaml /root/.config/yandex-cloud/config.yaml

RUN yc config list
RUN yc config profile activate default

FROM base as debug
RUN pip install pydevd-pycharm~=242.24807.21
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]

FROM base AS production
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]