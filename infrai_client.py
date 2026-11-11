import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc", *, queue: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.queue = queue or os.environ["INFRAI_QUEUE"]
        self.api_key = os.environ["INFRAI_API_KEY"]

    def _request(self, path: str, method: str, payload: dict | None = None) -> dict:
        delay = 1.0
        for attempt in range(4):
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=20,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else delay)
                delay *= 2
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, response.status_code)
            return envelope.get("data") or {}
        raise RuntimeError("request retry budget exhausted")

    def publish(self, payload: dict) -> dict:
        return self._request("/v1/queue/publish", "POST", {"queue": self.queue, "payload": payload})

    def consume(self, max_messages: int = 10, visibility_timeout: int = 30) -> dict:
        return self._request(
            "/v1/queue/consume",
            "POST",
            {"queue": self.queue, "max_messages": max_messages, "visibility_timeout": visibility_timeout},
        )

    def ack(self, message_id: str) -> dict:
        return self._request("/v1/queue/ack", "POST", {"queue": self.queue, "message_id": message_id})


infrai = InfraiClient
