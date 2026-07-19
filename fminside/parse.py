from __future__ import annotations

import re
import unicodedata
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from fminside.config import BASE_URL
from fminside.models import (
    ATTR_AEREO,
    ATTR_ATAQUE,
    ATTR_DEFESA,
    ATTR_FISICO,
    ATTR_MENTAL,
    ATTR_POS_GK,
    ATTR_REFLEXOS,
    ATTR_SAIDA,
    ATTR_TECNICA,
    POSICAO_FORMULARIO,
)

RE_PLAYER = re.compile(
    r"^https://fminside\.net/players/\d+-fm-\d+/\d+-[a-z0-9-]+$",
    re.IGNORECASE,
)
RE_FM_ID = re.compile(r"/(\d+)-[a-z0-9-]+/?$", re.IGNORECASE)
RE_INT = re.compile(r"-?\d+")


def limpar(texto: Optional[str]) -> str:
    if not texto:
        return ""
    return " ".join(texto.replace("\xa0", " ").replace("\u200b", "").split())


def slugify(texto: str) -> str:
    if not texto:
        return "sem_clube"
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")
    return slug or "sem_clube"


def absolutizar(href: str) -> str:
    return urljoin(BASE_URL + "/", href.lstrip("/"))


def normalizar_url_jogador(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def url_valida_jogador(url: str) -> bool:
    return bool(RE_PLAYER.match(normalizar_url_jogador(url)))


def extrair_fm_id(url: str) -> Optional[int]:
    m = RE_FM_ID.search(urlparse(url).path)
    return int(m.group(1)) if m else None


def eh_jogador_feminino(html: str) -> bool:
    return "/logos/women/" in html.lower()


def parse_int(texto: str) -> Optional[int]:
    m = RE_INT.search(texto or "")
    return int(m.group(0)) if m else None


def mapa_info(soup: BeautifulSoup) -> dict[str, str]:
    dados: dict[str, str] = {}
    for li in soup.select("#player_info li"):
        chave = li.select_one(".key")
        valor = li.select_one(".value")
        if not chave or not valor:
            continue
        dados[limpar(chave.get_text())] = limpar(valor.get_text(" ", strip=True))
    return dados


def perna_preferida(info: dict[str, str]) -> str:
    left = parse_int(info.get("Left foot", ""))
    right = parse_int(info.get("Right foot", ""))
    if left is None and right is None:
        return ""
    if left is None:
        return "Direito"
    if right is None:
        return "Esquerdo"
    if left == right:
        return "Ambidestro"
    return "Direito" if right > left else "Esquerdo"


def extrair_posicoes_fm(soup: BeautifulSoup, info: dict[str, str]) -> list[str]:
    naturais = [
        limpar(span.get_text())
        for span in soup.select(
            "#player_info .meta .desktop_positions .position.natural"
        )
    ]
    if naturais:
        return list(dict.fromkeys(naturais))
    bruto = info.get("Position(s)", "") or info.get("Position", "")
    tokens = re.findall(r"\b(?:GK|D[LCR]|WB[LR]|DM|M[LCR]|AM[LCR]|ST)\b", bruto)
    return list(dict.fromkeys(tokens))


def mapear_posicoes_formulario(posicoes_fm: list[str]) -> str:
    mapped: list[str] = []
    for pos in posicoes_fm:
        dest = POSICAO_FORMULARIO.get(pos.upper())
        if dest and dest not in mapped:
            mapped.append(dest)
    return ", ".join(mapped)


def extrair_atributos_brutos(soup: BeautifulSoup) -> dict[str, int]:
    attrs: dict[str, int] = {}
    for tr in soup.select("tr[id]"):
        nome_el = tr.select_one("td.name")
        valor_el = tr.select_one("td.stat")
        if not nome_el or not valor_el:
            continue
        nome = limpar(nome_el.get_text())
        valor = parse_int(limpar(valor_el.get_text()))
        if nome and valor is not None:
            attrs[nome] = valor
    return attrs


def media_grupo(attrs: dict[str, int], chaves: tuple[str, ...]) -> Optional[int]:
    valores = [attrs[k] for k in chaves if k in attrs]
    if not valores:
        return None
    return int(round(sum(valores) / len(valores)))


def agregar_notas_formulario(
    attrs: dict[str, int],
    potencial: Optional[int],
    eh_goleiro: bool,
) -> dict[str, Optional[int]]:
    mental = media_grupo(attrs, ATTR_MENTAL)
    if eh_goleiro:
        return {
            "Tecnica": None,
            "Ataque": None,
            "Defesa": None,
            "Fisico": None,
            "Reflexos": media_grupo(attrs, ATTR_REFLEXOS),
            "Posicionamento": media_grupo(attrs, ATTR_POS_GK),
            "JogoAereo": media_grupo(attrs, ATTR_AEREO),
            "SaidaDeBola": media_grupo(attrs, ATTR_SAIDA),
            "Mental": mental,
            "Talento": potencial,
        }
    return {
        "Tecnica": media_grupo(attrs, ATTR_TECNICA),
        "Ataque": media_grupo(attrs, ATTR_ATAQUE),
        "Defesa": media_grupo(attrs, ATTR_DEFESA),
        "Fisico": media_grupo(attrs, ATTR_FISICO),
        "Reflexos": None,
        "Posicionamento": None,
        "JogoAereo": None,
        "SaidaDeBola": None,
        "Mental": mental,
        "Talento": potencial,
    }


def parse_valor_euros(texto: str) -> Optional[int]:
    if not texto:
        return None
    t = limpar(texto)
    if "not for sale" in t.lower() or t in {"-", "n/a"}:
        return None
    completo = re.search(r"€?\s*(\d{1,3}(?:,\d{3})+)", t)
    if completo:
        return int(completo.group(1).replace(",", ""))
    partes = re.findall(r"€?\s*(\d+(?:\.\d+)?)\s*([KMBkmb])?", t)
    if not partes:
        digits = re.sub(r"[^\d]", "", t)
        return int(digits) if digits else None
    mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    valores: list[int] = []
    for num, suf in partes:
        fator = mult.get((suf or "").lower(), 1)
        valores.append(int(round(float(num) * fator)))
    if len(valores) >= 2:
        return int(round(sum(valores[:2]) / 2))
    return valores[0] if valores else None


def extrair_nacionalidade(soup: BeautifulSoup) -> str:
    flag = soup.select_one("#player_info .meta a[href^='/players/'] .flag")
    if flag and flag.parent:
        return limpar(flag.parent.get_text())
    img = soup.select_one("#player_info .meta img.flag")
    if img and img.get("code"):
        return limpar(str(img["code"]))
    return ""


def extrair_abilities(soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
    cards = soup.select("#player_info .meta > span.card")
    valores = [parse_int(limpar(c.get_text())) for c in cards]
    valores = [v for v in valores if v is not None]
    ca = valores[0] if len(valores) >= 1 else None
    pa = valores[1] if len(valores) >= 2 else None
    return ca, pa


def extrair_links_jogador(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    encontrados: list[str] = []
    vistos: set[str] = set()
    rows = soup.select("ul.player")
    nos = rows if rows else [soup]
    for row in nos:
        if eh_jogador_feminino(str(row)):
            continue
        for a in row.select("a[href*='/players/']"):
            href = a.get("href")
            if not href or not isinstance(href, str):
                continue
            url = normalizar_url_jogador(absolutizar(href))
            if not url_valida_jogador(url) or url in vistos:
                continue
            vistos.add(url)
            encontrados.append(url)
    return encontrados


def tem_load_more(html: str) -> bool:
    return 'class="loadmore"' in html or "Load more players" in html


def titulo_h1(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("#player_info h1") or soup.find("h1")
    if isinstance(h1, Tag) and h1.has_attr("title"):
        nome = limpar(str(h1.get("title")))
        if nome:
            return nome
    if h1:
        return limpar(h1.get_text())
    return ""
