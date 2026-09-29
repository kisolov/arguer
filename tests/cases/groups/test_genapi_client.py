from unittest.mock import Mock

import pytest
import requests

from src.domain.exceptions import LanguageModelError
from src.domain.models import ChatMessage
from src.infrastructure.genapi import GenAPIError
from tests.cases.base import BaseTestGroup


def http_response(json_body=None, status_code=200, text=""):
    response = Mock(status_code=status_code, text=text)
    response.json.return_value = json_body
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=response
        )
    return response


class TestGenAPIClient(BaseTestGroup):
    @pytest.fixture
    def client(self):
        client = self.container.adapters.genapi_client()
        client._session = Mock()
        return client

    @pytest.mark.asyncio
    async def test_complete_sends_sync_chat_payload_and_returns_text(self, client):
        client._session.post.return_value = http_response(
            {"response": [{"message": {"content": "ответ"}}]}
        )

        result = await client.complete(
            [ChatMessage("system", "промпт"), ChatMessage("user", "привет")]
        )

        assert result == "ответ"
        _, kwargs = client._session.post.call_args
        assert kwargs["json"] == {
            "messages": [
                {"role": "system", "content": "промпт"},
                {"role": "user", "content": "привет"},
            ],
            "is_sync": True,
        }
        assert client._session.post.call_args.args[0].endswith(
            f"/networks/{client.settings.model}"
        )

    @pytest.mark.asyncio
    async def test_http_error_is_language_model_error(self, client):
        client._session.post.return_value = http_response(
            status_code=500, text="boom"
        )

        with pytest.raises(LanguageModelError) as exc:
            await client.complete([ChatMessage("user", "привет")])

        assert isinstance(exc.value, GenAPIError)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_network_failure_is_language_model_error(self, client):
        client._session.post.side_effect = requests.exceptions.ConnectionError("down")

        with pytest.raises(LanguageModelError):
            await client.complete([ChatMessage("user", "привет")])

    @pytest.mark.asyncio
    async def test_unexpected_response_shape_is_language_model_error(self, client):
        client._session.post.return_value = http_response({"response": []})

        with pytest.raises(LanguageModelError):
            await client.complete([ChatMessage("user", "привет")])

    @pytest.mark.asyncio
    async def test_error_field_in_response_is_language_model_error(self, client):
        client._session.post.return_value = http_response({"error": "quota exceeded"})

        with pytest.raises(LanguageModelError, match="quota exceeded"):
            await client.complete([ChatMessage("user", "привет")])
