"""Образ бота: без секретов внутри, не от root, код в самом образе."""

import re
from pathlib import Path

from tests.cases.base import BaseTestGroup

ROOT = Path(__file__).resolve().parents[3]


def instructions(name: str) -> list[str]:
    # Склеиваем продолжения строк: одна инструкция — одна строка
    dockerfile = re.sub(r"\\\s*\n", " ", (ROOT / "docker/bot/Dockerfile").read_text())
    return [
        line.strip()
        for line in dockerfile.splitlines()
        if re.match(rf"\s*{name}\b", line)
    ]


class TestBotImage(BaseTestGroup):
    def test_service_account_key_is_not_baked_in(self):
        assert not any("yc_config" in line for line in instructions("COPY"))

    def test_secrets_stay_out_of_build_context(self):
        ignored = (ROOT / ".dockerignore").read_text().splitlines()

        assert {".env", "yc_config.yaml", ".git"} <= set(ignored)

    def test_bot_does_not_run_as_root(self):
        users = instructions("USER")

        assert users and users[-1] != "USER root"

    def test_ffmpeg_comes_from_distribution(self):
        run = " ".join(instructions("RUN"))

        assert "ffmpeg" in run and "apt-get install" in run
        assert "johnvansickle" not in run

    def test_code_is_part_of_image(self):
        assert "COPY --chown=app:app . ." in instructions("COPY")


class TestComposeBotService(BaseTestGroup):
    def volumes(self) -> list[str]:
        # PyYAML в зависимостях нет: секция сервиса разбирается как текст
        compose = (ROOT / "docker-compose.yaml").read_text()
        bot = compose.split("\n  telegram-bot:", 1)[1].split("\n\n", 1)[0]
        return re.findall(r"^\s+- (\./\S+)$", bot, flags=re.MULTILINE)

    def test_code_is_not_mounted_from_host(self):
        targets = [v.split(":")[1] for v in self.volumes()]

        assert targets
        assert not any(t.startswith(("/app/src", "/app/main.py")) for t in targets)

    def test_yc_key_is_mounted_read_only(self):
        key = [v for v in self.volumes() if v.startswith("./yc_config.yaml:")]

        assert key and key[0].endswith(":ro")
