import subprocess

from src.domain.models import Token
from src.domain.ports import TokenProvider

# Сколько токен хранится в Redis. Сам IAM-токен живёт дольше (до 12 часов)
TOKEN_TTL_SECONDS = 3600


class YCCLIWrapper(TokenProvider):
    def __init__(self, yc_cli_path: str):
        self.cli_path = yc_cli_path

    def create_token(self) -> Token:
        try:
            result = subprocess.run(
                [self.cli_path, "iam", "create-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            return Token(result.stdout.strip(), TOKEN_TTL_SECONDS)

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Command failed with code {e.returncode}\n"
                f"STDOUT: {e.stdout}\n"
                f"STDERR: {e.stderr}\n"
                f"Full command: {' '.join(e.cmd)}"
            )
            raise RuntimeError(f"Failed to create YC IAM token:\n{error_msg}") from e

        except Exception as e:
            raise RuntimeError(f"Unexpected error in YC CLI: {str(e)}") from e
