from __future__ import annotations

import logging
from typing import Callable, Iterable, Optional

from fminside.config import FILTER_URL, LISTING_URL, TABLE_URL
from fminside.http import ResilientHttpClient
from fminside.parse import extrair_links_jogador

log = logging.getLogger("fminside")

ProgressCb = Callable[[str, dict], None]


class PlayersUrlCrawler:
    def __init__(
        self,
        http: ResilientHttpClient,
        club: str = "",
        league: str = "",
        nationality: str = "",
        max_load_more: Optional[int] = None,
        on_progress: Optional[ProgressCb] = None,
    ) -> None:
        self._http = http
        self._club = (club or "").strip()
        self._league = (league or "").strip()
        self._nationality = (nationality or "").strip()
        self._max_load_more = max_load_more
        self._on_progress = on_progress

    def _emit(self, stage: str, **payload: object) -> None:
        if self._on_progress:
            self._on_progress(stage, payload)

    def crawl(self) -> list[str]:
        fila: list[str] = []
        vistos: set[str] = set()

        filtro_desc = []
        if self._club:
            filtro_desc.append(f"clube={self._club}")
        if self._league:
            filtro_desc.append(f"liga={self._league}")
        if self._nationality:
            filtro_desc.append(f"nação={self._nationality}")
        log.info(
            "Fase 1: listagem masculinos%s",
            f" ({', '.join(filtro_desc)})" if filtro_desc else "",
        )
        self._emit(
            "crawl_start",
            club=self._club,
            league=self._league,
            nationality=self._nationality,
        )

        page = self._http.get(LISTING_URL)
        if page is None:
            log.error("Não foi possível carregar a listagem inicial")
            return []
        self._http.sleep()

        self._http.post(
            FILTER_URL,
            data={
                "page": "players",
                "database_version": "7",
                "gender": "1",
                "name": "",
                "uid": "",
                "club": self._club,
                "nationality": self._nationality,
                "league": self._league,
            },
            headers={
                "Referer": LISTING_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        self._http.sleep()

        tabela = self._http.get(
            TABLE_URL,
            params={"ajax_request": "1"},
            headers={
                "Referer": LISTING_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
            },
        )
        html_inicial = tabela.text if tabela and tabela.text.strip() else page.text
        self._acrescentar(fila, vistos, extrair_links_jogador(html_inicial))
        log.info("Página inicial: %s URLs", len(fila))
        self._emit("crawl_page", urls=len(fila), batch=0)
        self._http.sleep()

        batch = 0
        while True:
            if self._max_load_more is not None and batch >= self._max_load_more:
                log.info("Limite MAX_LOAD_MORE=%s atingido", self._max_load_more)
                break

            resp = self._http.get(
                TABLE_URL,
                params={"ajax_request": "1", "loadmore": "true"},
                headers={
                    "Referer": LISTING_URL,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "*/*",
                },
            )
            if resp is None or not resp.text.strip():
                log.info("Load more sem conteúdo — fim da paginação")
                break

            novos = extrair_links_jogador(resp.text)
            antes = len(fila)
            self._acrescentar(fila, vistos, novos)
            adicionados = len(fila) - antes
            batch += 1
            log.info("Load more #%s: +%s (total %s)", batch, adicionados, len(fila))
            self._emit(
                "crawl_page",
                urls=len(fila),
                batch=batch,
                added=adicionados,
            )

            # Sem URLs novas = fim. O HTML do site pode continuar com
            # class="loadmore" mesmo sem mais resultados (loop infinito).
            if adicionados == 0:
                log.info("Load more sem URLs novas — fim da paginação")
                break
            self._http.sleep()

        self._emit("crawl_done", urls=len(fila))
        return fila

    @staticmethod
    def _acrescentar(fila: list[str], vistos: set[str], urls: Iterable[str]) -> None:
        for url in urls:
            if url not in vistos:
                vistos.add(url)
                fila.append(url)
