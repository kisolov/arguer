"""Ответ модели в Telegram: промпт просит <b> и <i>, остальное должно уйти как текст."""

import html
import re
from typing import List

MESSAGE_LIMIT = 4096
ALLOWED_TAGS = ("b", "i", "u", "s", "code")

_ESCAPED_TAG = re.compile(r"&lt;(/?)(%s)&gt;" % "|".join(ALLOWED_TAGS))
_TAG = re.compile(r"<(/?)(%s)>" % "|".join(ALLOWED_TAGS))


def to_telegram_html(text: str) -> str:
    """Экранирует всё, кроме простых разрешённых тегов.

    Если разрешённые теги не сбалансированы, Telegram отклонил бы сообщение
    целиком, поэтому тогда теги убираются и текст уходит без разметки.
    """
    escaped = _ESCAPED_TAG.sub(r"<\1\2>", html.escape(text, quote=False))
    if _balanced(escaped):
        return escaped
    return _TAG.sub("", escaped)


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> List[str]:
    """Режет текст на части не длиннее limit, по возможности по строкам.

    Лимит Telegram считается по тексту без разметки, поэтому длина исходного
    текста с тегами — оценка сверху.
    """
    chunks: List[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit + 1)
        if cut <= 0:
            cut = limit
        chunks.append(rest[:cut])
        rest = rest[cut:].lstrip("\n")
    if rest or not chunks:
        chunks.append(rest)
    return chunks


def _balanced(markup: str) -> bool:
    stack: List[str] = []
    for closing, tag in _TAG.findall(markup):
        if not closing:
            stack.append(tag)
        elif not stack or stack.pop() != tag:
            return False
    return not stack
