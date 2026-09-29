from typing import Optional, Any, Dict, Union

from pydantic import BaseModel


class LLMOutput(BaseModel):
    generated_output: Optional[Any] = None
    full_response: Optional[Dict[str, Any]] = None
    request_id: Optional[Union[int, str]] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error_message is None and self.generated_output is not None
