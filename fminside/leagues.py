from __future__ import annotations

import json
import logging
from pathlib import Path

from bs4 import BeautifulSoup

from fminside.config import LISTING_URL, OUTPUT_DIR
from fminside.http import ResilientHttpClient

log = logging.getLogger("fminside")

LEAGUES_CACHE = OUTPUT_DIR / "leagues_cache.json"
NATIONS_CACHE = OUTPUT_DIR / "nations_cache.json"


def _extrair_valores(html: str, seletor: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    nomes: list[str] = []
    vistos: set[str] = set()
    for a in soup.select(seletor):
        valor = (a.get("value") or "").strip()
        if not valor or valor in vistos:
            continue
        vistos.add(valor)
        nomes.append(valor)
    return sorted(nomes, key=str.casefold)


def extrair_ligas_do_html(html: str) -> list[str]:
    return _extrair_valores(html, "div.leagues a[value]")


def extrair_nacoes_do_html(html: str) -> list[str]:
    return _extrair_valores(html, "div.nations a[value]")


def _carregar_lista(
    cache_path: Path,
    extrair,
    label: str,
    force_refresh: bool = False,
) -> list[str]:
    if cache_path.exists() and not force_refresh:
        with cache_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list) and data:
            return data

    http = ResilientHttpClient()
    resp = http.get(LISTING_URL)
    if resp is None:
        log.error("Falha ao obter listagem para cache de %s", label)
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return []

    # Uma única request alimenta ligas e nações
    ligas = extrair_ligas_do_html(resp.text)
    nacoes = extrair_nacoes_do_html(resp.text)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with LEAGUES_CACHE.open("w", encoding="utf-8") as fh:
        json.dump(ligas, fh, ensure_ascii=False, indent=2)
    with NATIONS_CACHE.open("w", encoding="utf-8") as fh:
        json.dump(nacoes, fh, ensure_ascii=False, indent=2)
    log.info("Cache: %s ligas, %s nações", len(ligas), len(nacoes))

    if label == "ligas":
        return ligas
    return nacoes


def carregar_ligas(force_refresh: bool = False) -> list[str]:
    return _carregar_lista(LEAGUES_CACHE, extrair_ligas_do_html, "ligas", force_refresh)


def carregar_nacoes(force_refresh: bool = False) -> list[str]:
    return _carregar_lista(NATIONS_CACHE, extrair_nacoes_do_html, "nacoes", force_refresh)
