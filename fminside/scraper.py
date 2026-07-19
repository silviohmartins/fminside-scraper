from __future__ import annotations

import logging
from typing import Optional

from bs4 import BeautifulSoup

from fminside.config import LISTING_URL
from fminside.http import ResilientHttpClient
from fminside.models import Jogador
from fminside.parse import (
    agregar_notas_formulario,
    calibrar_notas_ao_ca,
    eh_jogador_feminino,
    extrair_abilities,
    extrair_atributos_brutos,
    extrair_fm_id,
    extrair_nacionalidade,
    extrair_posicoes_fm,
    limpar,
    mapa_info,
    mapear_posicoes_formulario,
    normalizar_url_jogador,
    parse_int,
    parse_valor_euros,
    perna_preferida,
    titulo_h1,
)

log = logging.getLogger("fminside")


class PlayerProfileScraper:
    def __init__(self, http: ResilientHttpClient) -> None:
        self._http = http

    def scrape(self, url: str) -> Optional[Jogador]:
        resp = self._http.get(url, headers={"Referer": LISTING_URL})
        if resp is None:
            return None

        if eh_jogador_feminino(resp.text):
            log.info("Ignorando jogadora feminina: %s", url)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        info = mapa_info(soup)
        nome = titulo_h1(soup)
        ca, pa = extrair_abilities(soup)
        attrs = extrair_atributos_brutos(soup)
        posicoes_fm = extrair_posicoes_fm(soup, info)
        posicoes = mapear_posicoes_formulario(posicoes_fm)
        eh_goleiro = (
            (posicoes.split(",")[0].strip().upper() == "G") if posicoes else False
        )
        notas = agregar_notas_formulario(attrs, pa, eh_goleiro)
        posicao_grupo = (
            posicoes.split(",")[0].strip().upper() if posicoes else None
        )
        notas = calibrar_notas_ao_ca(notas, posicao_grupo, ca)

        clube = info.get("Club", "")
        if not clube:
            club_el = soup.select_one("#player_info .meta a[href*='/clubs/'] .value")
            clube = limpar(club_el.get_text()) if club_el else ""

        valor_txt = info.get("Sell value", "") or info.get("Value", "")
        if not valor_txt:
            price = soup.select_one("#player_info .player_value .price")
            valor_txt = limpar(price.get_text(" ", strip=True)) if price else ""

        return Jogador(
            Url=normalizar_url_jogador(url),
            Genero="Masculino",
            FmId=extrair_fm_id(url),
            Nome=nome,
            Nacao=extrair_nacionalidade(soup),
            Clube=clube,
            Idade=parse_int(info.get("Age", "")),
            PePreferido=perna_preferida(info),
            Posicoes=posicoes,
            Tecnica=notas["Tecnica"],
            Ataque=notas["Ataque"],
            Defesa=notas["Defesa"],
            Fisico=notas["Fisico"],
            Reflexos=notas["Reflexos"],
            Posicionamento=notas["Posicionamento"],
            JogoAereo=notas["JogoAereo"],
            SaidaDeBola=notas["SaidaDeBola"],
            Mental=notas["Mental"],
            Talento=notas["Talento"],
            ValorMercado=parse_valor_euros(valor_txt),
            AbilityAtual=ca,
            PosicoesFm=", ".join(posicoes_fm),
            Salario=info.get("Wages", "") or info.get("Wage", ""),
            VencimentoContrato=info.get("Contract end", ""),
        )
