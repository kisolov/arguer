import asyncio
import time
from typing import Any, Dict, Optional, Sequence

import requests

from config import GenAPIConfig
from src.domain.exceptions import LanguageModelError
from src.domain.models import ChatMessage
from src.domain.ports import LanguageModelInterface


class GenAPIError(LanguageModelError):
    """Ошибка обращения к GenAPI."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _is_transient(error: GenAPIError) -> bool:
    """Сеть, таймаут (status_code нет), перегрузка или сбой сервера."""
    return error.status_code is None or error.status_code == 429 or error.status_code >= 500


class GenAPIClient(LanguageModelInterface):
    def __init__(self, settings: GenAPIConfig):
        self.settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.settings.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            }
        )

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "is_sync": True,
        }
        data = await asyncio.to_thread(self._post, f"networks/{self.settings.model}", payload)
        return self._extract_content(data)

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняется в потоке, поэтому пауза между попытками — обычный sleep."""
        attempt = 0
        while True:
            try:
                return self._post_once(endpoint, payload)
            except GenAPIError as error:
                if attempt >= self.settings.max_retries or not _is_transient(error):
                    raise
                time.sleep(self.settings.retry_backoff_seconds * 2**attempt)
                attempt += 1

    def _post_once(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.settings.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = self._session.post(
                url, json=payload, timeout=self.settings.default_timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text[:500]}"
            raise GenAPIError(error_msg, e.response.status_code) from e
        except requests.exceptions.RequestException as e:
            raise GenAPIError(f"Request failed: {e}") from e

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        if data.get("error"):
            raise GenAPIError(str(data["error"]))
        try:
            return data["response"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise GenAPIError(f"Unexpected response shape: {e!r}") from e
