import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Raised when a stored secret cannot be decrypted with the configured key."""


class SecretBox:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt_json(self, value: dict[str, Any]) -> str:
        return self._fernet.encrypt(json.dumps(value).encode()).decode()

    def decrypt_json(self, token: str) -> dict[str, Any]:
        try:
            return json.loads(self._fernet.decrypt(token.encode()))
        except InvalidToken as exc:
            raise DecryptionError(
                "Stored secret cannot be decrypted with the current FORGEOPS_SECRET_KEY"
            ) from exc
