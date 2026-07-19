from __future__ import annotations

import logging
import random
import time
from typing import Optional

import requests

from fminside.config import (
    DELAY_MAX_S,
    DELAY_MIN_S,
    HEADERS,
    MAX_RETRIES,
    REQUEST_TIMEOUT_S,
    SKIP_HTTP_STATUS,
)

log = logging.getLogger("fminside")


class ResilientHttpClient:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        delay_min: float = DELAY_MIN_S,
        delay_max: float = DELAY_MAX_S,
        timeout: int = REQUEST_TIMEOUT_S,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(HEADERS)
        self._delay_min = delay_min
        self._delay_max = delay_max
        self._timeout = timeout
        self._max_retries = max_retries

    @property
    def session(self) -> requests.Session:
        return self._session

    def sleep(self) -> None:
        time.sleep(random.uniform(self._delay_min, self._delay_max))

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        kwargs.setdefault("timeout", self._timeout)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.request(method, url, **kwargs)
            except requests.Timeout:
                log.warning("Timeout (%s/%s): %s", attempt, self._max_retries, url)
                time.sleep(min(10 * attempt, 40))
                continue
            except requests.ConnectionError as exc:
                log.warning(
                    "Conexão (%s/%s): %s — %s",
                    attempt,
                    self._max_retries,
                    url,
                    exc,
                )
                time.sleep(min(10 * attempt, 40))
                continue
            except requests.RequestException as exc:
                log.error("Erro de request em %s: %s", url, exc)
                return None

            status = response.status_code
            if status == 200:
                if "Just a moment" in response.text:
                    log.warning("Cloudflare challenge em %s — pulando", url)
                    return None
                return response

            if status == 429:
                wait = 15 * attempt
                log.warning("HTTP 429 em %s — aguardando %ss", url, wait)
                time.sleep(wait)
                continue

            if status in SKIP_HTTP_STATUS:
                log.error("HTTP %s em %s — pulando", status, url)
                return None

            log.error("HTTP %s em %s", status, url)
            return None

        log.error("Esgotadas tentativas para %s", url)
        return None
