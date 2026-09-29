import asyncio
import time
from typing import Any, Dict, Optional
import requests
from pydantic import BaseModel
from config import GenAPIConfig

from src.domain.ports import LanguageModelInterface
from src.domain.models.llm_output import LLMOutput


class GenAPIResponse(BaseModel):
    """Унифицированная модель ответа GenAPI"""

    request_id: Optional[int] = None
    output: Optional[Any] = None
    error: Optional[str] = None

    def __init__(self, response: Optional[Dict] = None, **data):
        super().__init__(**data)
        if response is not None:
            self.output = response[0]["message"]["content"]


class GenAPIError(Exception):
    """Базовое исключение для ошибок GenAPI."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


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

    def _request(
        self, method: str, endpoint: str, json_data: Optional[Dict] = None
    ) -> Dict:
        url = f"{self.settings.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = self._session.request(
                method,
                url,
                json=json_data,
                timeout=self.settings.default_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text[:500]}"
            raise GenAPIError(error_msg, e.response.status_code)
        except requests.exceptions.RequestException as e:
            raise GenAPIError(f"Request failed: {str(e)}")

    async def generate(
        self,
        payload: Dict[str, Any],
        is_function: bool = False,
        prefer_sync_api_call: bool = True,
    ) -> LLMOutput:
        try:
            endpoint = "functions" if is_function else "networks"
            endpoint = f"{endpoint}/{self.settings.model}"

            if prefer_sync_api_call:
                payload["is_sync"] = True
                response = await self._execute_sync(endpoint, payload)
            else:
                response = await self._execute_async(endpoint, payload)

            return LLMOutput(
                generated_output=response.output,
                full_response=response.model_dump(),
                request_id=response.request_id,
                error_message=response.error,
            )

        except GenAPIError as e:
            return LLMOutput(error_message=str(e), full_response={}, request_id=None)
        except Exception as e:
            return LLMOutput(
                error_message=f"Unexpected error: {str(e)}",
                full_response={},
                request_id=None,
            )

    async def _execute_sync(self, endpoint: str, payload: Dict) -> GenAPIResponse:
        data = await asyncio.to_thread(self._request, "POST", endpoint, payload)
        return GenAPIResponse(**data)

    async def _execute_async(self, endpoint: str, payload: Dict) -> GenAPIResponse:
        # Start async operation
        init_data = await asyncio.to_thread(self._request, "POST", endpoint, payload)
        if not init_data.get("request_id"):
            raise GenAPIError("No request_id in initial response")

        # Poll for results
        return await asyncio.to_thread(self._poll_results, init_data["request_id"])

    def _poll_results(self, request_id: str) -> GenAPIResponse:
        start_time = time.monotonic()

        while True:
            if time.monotonic() - start_time > self.settings.long_poll_timeout_seconds:
                raise GenAPIError("Polling timeout exceeded")

            data = self._request("GET", f"request/get/{request_id}")
            response = GenAPIResponse(**data)

            if response.output is not None:
                return response
            elif response.error:
                raise GenAPIError(response.error)

            time.sleep(self.settings.default_poll_interval_seconds)
