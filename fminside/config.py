from __future__ import annotations

from pathlib import Path
from typing import Optional

BASE_URL = "https://fminside.net"
LISTING_URL = f"{BASE_URL}/players"
FILTER_URL = f"{BASE_URL}/resources/inc/ajax/update_filter.php"
TABLE_URL = (
    f"{BASE_URL}/beheer/modules/players/resources/inc/frontend/"
    "generate-player-table.php"
)

OUTPUT_DIR = Path("output")
DELAY_MIN_S = 1.5
DELAY_MAX_S = 3.5
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 4

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{BASE_URL}/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

SKIP_HTTP_STATUS = {403, 404, 500}

# Limites opcionais (None = sem limite)
DEFAULT_MAX_LOAD_MORE: Optional[int] = None
DEFAULT_MAX_PROFILES: Optional[int] = None
