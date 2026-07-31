from __future__ import annotations

import secrets
import string

_ALPHABET = string.ascii_letters + string.digits


def generate_token(length: int = 12) -> str:
    """URL-safe, human-typeable token for the anonymous deep link."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
