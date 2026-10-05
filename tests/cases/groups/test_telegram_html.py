"""Ответ модели доходит до Telegram: разметка безопасна, длина в лимите."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.models import MessageContext, User
from src.infrastructure import AiogramMessageService
from src.infrastructure.aiogram.telegram_html import (
    MESSAGE_LIMIT,
    split_message,
    to_telegram_html,
)
from tests.cases.base import BaseTestGroup


class TestTelegramHtml(BaseTestGroup):
    def test_allowed_tags_are_kept(self):
        text = "1. <b>Довод</b> — <i>курсив</i> и <code>код</code>"

        assert to_telegram_html(text) == text

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("x < y && y > z", "x &lt; y &amp;&amp; y &gt; z"),
            ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ],
    )
    def test_everything_else_is_escaped(self, raw, expected):
        assert to_telegram_html(raw) == expected

    def test_tag_with_attributes_is_not_trusted(self):
        # Открывающий тег с атрибутом экранирован, одинокий </b> ломал бы разбор
        assert to_telegram_html('<b class="x">жирный</b>') == (
            '&lt;b class="x"&gt;жирный'
        )

    @pytest.mark.parametrize(
        "raw",
        ["<b>не закрыт", "закрыт без открытия</i>", "<b><i>крест</b></i>"],
    )
    def test_broken_markup_is_sent_as_plain_text(self, raw):
        result = to_telegram_html(raw)

        assert "<b>" not in result and "<i>" not in result
        assert "</b>" not in result and "</i>" not in result

    def test_short_text_is_one_chunk(self):
        assert split_message("коротко") == ["коротко"]

    def test_empty_text_is_one_empty_chunk(self):
        assert split_message("") == [""]

    def test_long_text_is_split_by_lines_within_limit(self):
        paragraph = "довод " * 100
        text = "\n".join(f"{i}. {paragraph}" for i in range(20))

        chunks = split_message(text)

        assert len(chunks) > 1
        assert all(len(c) <= MESSAGE_LIMIT for c in chunks)
        assert all(c.split(". ", 1)[0].isdigit() for c in chunks)
        assert "\n".join(chunks) == text

    def test_text_without_newlines_is_cut_hard(self):
        chunks = split_message("я" * (MESSAGE_LIMIT * 2 + 10))

        assert [len(c) for c in chunks] == [MESSAGE_LIMIT, MESSAGE_LIMIT, 10]


class TestResolutionDelivery(BaseTestGroup):
    @pytest.fixture
    def bot(self):
        bot = Mock()
        bot.send_message = AsyncMock(return_value=Mock(message_id=1))
        return bot

    @pytest.mark.asyncio
    async def test_long_unsafe_resolution_is_sent_in_safe_parts(self, bot):
        resolution = "\n".join(f"{i}. <b>довод</b> a < b " + "x" * 300 for i in range(40))

        await AiogramMessageService(bot).send_resolution(
            MessageContext(User(telegram_id=5, id=1)), resolution
        )

        texts = [c.kwargs["text"] for c in bot.send_message.await_args_list]
        assert len(texts) > 1
        assert all("a &lt; b" in t and "<b>довод</b>" in t for t in texts)
        visible = [t.replace("<b>", "").replace("</b>", "") for t in texts]
        assert all(len(v.replace("&lt;", "<")) <= MESSAGE_LIMIT for v in visible)
