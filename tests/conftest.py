from __future__ import annotations

import json
from typing import Any


class FakeResponseCtx:
    """Context-manager fake for urllib.request.urlopen responses."""

    def __init__(self, body: bytes):
        self._body = body

    @classmethod
    def json(cls, payload: Any) -> "FakeResponseCtx":
        return cls(json.dumps(payload).encode())

    def __enter__(self) -> "FakeResponseCtx":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def read(self) -> bytes:
        return self._body
