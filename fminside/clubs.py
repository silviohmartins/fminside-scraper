from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from bs4 import BeautifulSoup

from fminside.config import BASE_URL, FILTER_URL
from fminside.http import ResilientHttpClient

log = logging.getLogger("fminside")

CLUBS_URL = f"{BASE_URL}/clubs"
CLUBS_TABLE_URL = (
    f"{BASE_URL}/beheer/modules/clubs/resources/inc/frontend/"
    "generate-club-table.php"
)

ProgressCb = Callable[[str, dict], None]

# Dicas para desambiguar ligas com o mesmo nome no filtro do site.
# O título real em li.league[title] diferencia (ex.: Brasileiro Série A vs Serie A).
NATION_LEAGUE_INCLUDE = {
    "Brazil": ("brasileiro",),
    "Italy": (),  # tratado à parte: Serie A sem "Brasileiro"
    "England": ("premier league", "championship", "league one", "league two"),
    "Spain": ("laliga",),
    "France": ("ligue",),
    "Germany": ("bundesliga",),
    "Portugal": ("liga portugal", "primeira liga"),
    "Argentina": ("liga profesional", "argentina"),
    "Netherlands": ("eredivisie",),
    "United States": ("mls",),
    "Mexico": ("liga bbva", "liga mx"),
}


@dataclass(frozen=True)
class ClubRef:
    name: str
    league_title: str
    href: str = ""


def _extrair_clubes_html(html: str) -> list[ClubRef]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[ClubRef] = []
    vistos: set[str] = set()
    for ul in soup.select("ul.club"):
        a = ul.select_one('li.club a[href*="/clubs/"]')
        liga_el = ul.select_one("li.league")
        if not a:
            continue
        nome = (a.get_text() or "").strip()
        if not nome or nome in vistos:
            continue
        title = ""
        if liga_el is not None:
            title = (liga_el.get("title") or liga_el.get_text(" ", strip=True) or "").strip()
        vistos.add(nome)
        out.append(ClubRef(name=nome, league_title=title, href=str(a.get("href") or "")))
    return out


def filtrar_clubes_por_nacao(
    clubes: list[ClubRef],
    nationality: str,
    league_query: str = "",
) -> list[ClubRef]:
    """Filtra pela liga real do clube (title), usando a nação pedida."""
    if not nationality or not clubes:
        return clubes

    nat = nationality.strip()
    titles = sorted({c.league_title for c in clubes if c.league_title})
    log.info("Títulos de liga encontrados: %s", titles)

    nat_l = nat.lower()
    include = NATION_LEAGUE_INCLUDE.get(nat, (nat_l,))

    # Itália: Serie A / Serie B sem "Brasileiro"
    if nat_l == "italy":
        escolhidos = [
            c
            for c in clubes
            if c.league_title
            and "brasileiro" not in c.league_title.lower()
            and (
                not league_query
                or league_query.casefold() in c.league_title.casefold()
                or c.league_title.casefold() in league_query.casefold()
            )
        ]
        # Se a query era Série A (com acento), aceita title Serie A
        if not escolhidos and league_query:
            base = league_query.replace("é", "e").replace("É", "E")
            escolhidos = [
                c
                for c in clubes
                if c.league_title
                and "brasileiro" not in c.league_title.lower()
                and base.casefold() in c.league_title.replace("é", "e").casefold()
            ]
        return escolhidos

    # Brasil e demais: title deve conter alguma dica da nação
    escolhidos = [
        c
        for c in clubes
        if c.league_title
        and any(h in c.league_title.lower() for h in include if h)
    ]
    if escolhidos:
        return escolhidos

    # Fallback: title contém o nome da nação
    escolhidos = [
        c for c in clubes if c.league_title and nat_l in c.league_title.lower()
    ]
    return escolhidos


class ClubsCrawler:
    """Lista clubes via /clubs (necessário para desambiguar ligas misturadas)."""

    def __init__(
        self,
        http: ResilientHttpClient,
        league: str = "",
        max_load_more: Optional[int] = None,
        on_progress: Optional[ProgressCb] = None,
    ) -> None:
        self._http = http
        self._league = (league or "").strip()
        self._max_load_more = max_load_more
        self._on_progress = on_progress

    def _emit(self, stage: str, **payload: object) -> None:
        if self._on_progress:
            self._on_progress(stage, payload)

    def crawl(self) -> list[ClubRef]:
        clubes: list[ClubRef] = []
        vistos: set[str] = set()

        log.info("Listando clubes (liga=%s)", self._league or "—")
        self._emit("clubs_start", league=self._league)

        page = self._http.get(CLUBS_URL)
        if page is None:
            log.error("Não foi possível abrir /clubs")
            return []
        self._http.sleep()

        self._http.post(
            FILTER_URL,
            data={
                "page": "clubs",
                "database_version": "7",
                "gender": "1",
                "name": "",
                "uid": "",
                "club": "",
                "nationality": "",
                "league": self._league,
            },
            headers={
                "Referer": CLUBS_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        self._http.sleep()

        tabela = self._http.get(
            CLUBS_TABLE_URL,
            params={"ajax_request": "1"},
            headers={
                "Referer": CLUBS_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
            },
        )
        html = tabela.text if tabela and tabela.text.strip() else page.text
        self._acrescentar(clubes, vistos, _extrair_clubes_html(html))
        self._emit("clubs_page", clubs=len(clubes), batch=0)
        self._http.sleep()

        batch = 0
        while True:
            if self._max_load_more is not None and batch >= self._max_load_more:
                break
            resp = self._http.get(
                CLUBS_TABLE_URL,
                params={"ajax_request": "1", "loadmore": "true"},
                headers={
                    "Referer": CLUBS_URL,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "*/*",
                },
            )
            if resp is None or not resp.text.strip():
                break
            antes = len(clubes)
            self._acrescentar(clubes, vistos, _extrair_clubes_html(resp.text))
            batch += 1
            added = len(clubes) - antes
            self._emit(
                "clubs_page",
                clubs=len(clubes),
                batch=batch,
                added=added,
            )
            if added == 0:
                break
            self._http.sleep()

        log.info("Clubes listados: %s", len(clubes))
        self._emit("clubs_done", clubs=len(clubes))
        return clubes

    @staticmethod
    def _acrescentar(
        dest: list[ClubRef],
        vistos: set[str],
        novos: list[ClubRef],
    ) -> None:
        for c in novos:
            if c.name not in vistos:
                vistos.add(c.name)
                dest.append(c)
