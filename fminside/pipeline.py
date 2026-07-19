from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from fminside.clubs import ClubsCrawler, filtrar_clubes_por_nacao
from fminside.config import (
    DEFAULT_MAX_LOAD_MORE,
    DEFAULT_MAX_PROFILES,
    OUTPUT_DIR,
)
from fminside.crawler import PlayersUrlCrawler
from fminside.export import salvar_jsons_por_clube
from fminside.http import ResilientHttpClient
from fminside.models import Jogador
from fminside.parse import slugify
from fminside.scraper import PlayerProfileScraper

log = logging.getLogger("fminside")

ProgressCb = Callable[[str, dict], None]


@dataclass
class ScrapeFilters:
    club: str = ""
    league: str = ""
    nationality: str = ""
    max_load_more: Optional[int] = DEFAULT_MAX_LOAD_MORE
    max_profiles: Optional[int] = DEFAULT_MAX_PROFILES
    output_dir: Path = OUTPUT_DIR


@dataclass
class ScrapeResult:
    jogadores: list[Jogador]
    files: list[Path]
    output_dir: Path


def _destino_saida(filters: ScrapeFilters) -> Path:
    if filters.club:
        return filters.output_dir / "clubs"
    if filters.league:
        liga = slugify(filters.league)
        if filters.nationality:
            return filters.output_dir / "leagues" / slugify(filters.nationality) / liga
        return filters.output_dir / "leagues" / liga
    if filters.nationality:
        return filters.output_dir / "nations" / slugify(filters.nationality)
    return filters.output_dir / "all"


def _scrape_urls(
    http: ResilientHttpClient,
    scraper: PlayerProfileScraper,
    urls: list[str],
    max_profiles: Optional[int],
    on_progress: Optional[ProgressCb],
) -> list[Jogador]:
    def emit(stage: str, **payload: object) -> None:
        if on_progress:
            on_progress(stage, payload)

    if max_profiles is not None:
        urls = urls[:max_profiles]

    emit("scrape_start", total=len(urls))
    jogadores: list[Jogador] = []

    for i, url in enumerate(urls, start=1):
        try:
            jogador = scraper.scrape(url)
            if jogador is None:
                emit("scrape_skip", done=i, total=len(urls), url=url)
                continue
            jogadores.append(jogador)
            emit(
                "scrape_player",
                done=i,
                total=len(urls),
                nome=jogador.Nome,
                clube=jogador.Clube,
            )
            log.info(
                "[%s/%s] %s | %s | %s",
                i,
                len(urls),
                jogador.Nome or "?",
                jogador.Clube,
                jogador.Posicoes,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Falha em %s: %s", url, exc)
            emit("scrape_error", done=i, total=len(urls), url=url, error=str(exc))
        finally:
            http.sleep()
    return jogadores


def run_scrape(
    filters: ScrapeFilters,
    on_progress: Optional[ProgressCb] = None,
) -> ScrapeResult:
    def emit(stage: str, **payload: object) -> None:
        if on_progress:
            on_progress(stage, payload)

    http = ResilientHttpClient()
    scraper = PlayerProfileScraper(http=http)
    urls: list[str] = []

    if filters.league:
        # Liga no fminside misture países (Série A BR + Serie A IT).
        # Resolvemos pelos clubes e pelo título real da liga.
        clubs_crawler = ClubsCrawler(
            http=http,
            league=filters.league,
            max_load_more=filters.max_load_more,
            on_progress=on_progress,
        )
        clubes = clubs_crawler.crawl()
        titles = sorted({c.league_title for c in clubes if c.league_title})
        if len(titles) > 1 and not filters.nationality:
            log.warning(
                "A liga '%s' retornou títulos mistos %s. "
                "Informe nationality/nação para desambiguar (ex.: Brazil ou Italy).",
                filters.league,
                titles,
            )
            emit("warn_mixed_leagues", titles=titles)

        if filters.nationality:
            antes = len(clubes)
            clubes = filtrar_clubes_por_nacao(
                clubes, filters.nationality, filters.league
            )
            log.info(
                "Filtro nação=%s: %s → %s clubes (%s)",
                filters.nationality,
                antes,
                len(clubes),
                sorted({c.league_title for c in clubes}),
            )
            emit(
                "clubs_filtered",
                clubs=len(clubes),
                titles=sorted({c.league_title for c in clubes if c.league_title}),
            )

        if not clubes:
            log.error("Nenhum clube restante após filtros de liga/nação")
            dest = _destino_saida(filters)
            emit("done", players=0, files=[], output_dir=str(dest))
            return ScrapeResult(jogadores=[], files=[], output_dir=dest)

        for club in clubes:
            emit("club_crawl", club=club.name, league_title=club.league_title)
            log.info("Coletando elenco: %s (%s)", club.name, club.league_title)
            player_crawler = PlayersUrlCrawler(
                http=http,
                club=club.name,
                league="",
                nationality="",
                max_load_more=filters.max_load_more,
                on_progress=on_progress,
            )
            urls.extend(player_crawler.crawl())

        seen: set[str] = set()
        uniq: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        urls = uniq

    else:
        crawler = PlayersUrlCrawler(
            http=http,
            club=filters.club,
            league="",
            nationality=filters.nationality,
            max_load_more=filters.max_load_more,
            on_progress=on_progress,
        )
        urls = crawler.crawl()

    jogadores = _scrape_urls(
        http, scraper, urls, filters.max_profiles, on_progress
    )

    dest = _destino_saida(filters)
    files = salvar_jsons_por_clube(jogadores, dest)
    emit(
        "done",
        players=len(jogadores),
        files=[str(p) for p in files],
        output_dir=str(dest),
    )
    log.info(
        "Concluído: %s jogadores → %s arquivos em %s",
        len(jogadores),
        len(files),
        dest,
    )
    return ScrapeResult(jogadores=jogadores, files=files, output_dir=dest)
