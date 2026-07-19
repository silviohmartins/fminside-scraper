from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from fminside.models import PE_LETRA, Jogador
from fminside.parse import slugify


def jogador_para_gofoot(j: Jogador) -> dict:
    """Formato de exportação do Gofoot Studio."""
    pe = PE_LETRA.get(j.PePreferido)
    saida: dict = {
        "id": f"fm_{j.FmId}" if j.FmId is not None else None,
        "nome": j.Nome or None,
        "idade": j.Idade,
        "nacionalidade": (j.Nacao or "").lower() or None,
        "numero": None,
        "pe": pe,
        "posicao": j.posicao_grupo(),
        "TAL": j.Talento,
        "salario": None,
        "valor": j.ValorMercado,
        "team_id": slugify(j.Clube) if j.Clube else None,
        "energia": 100,
        "lesionado": None,
        "diasLesao": None,
        "suspenso": False,
        "fimContrato": None,
        "cartoes_amarelos": None,
        "cartoes_vermelhos": None,
        "golsCarreira": None,
        "golsTemporada": None,
        "assistenciasCarreira": None,
        "assistenciasTemporada": None,
        "jogosCarreira": None,
        "jogosTemporada": None,
        "caracteristicas": None,
        "avatar_body": None,
        "avatar_body_color": None,
        "avatar_body_white_mix": None,
        "avatar_hair": None,
        "avatar_hair_color": None,
        "avatar_hair_white_mix": None,
        "avatar_beard": None,
        "avatar_beard_color": None,
        "avatar_beard_white_mix": None,
        "avatar_shirt": None,
        "avatar_color": None,
        "avatar_earring": None,
        "avatar_earring_color": None,
        "avatar_earring_white_mix": None,
        "avatar_tattoo": None,
        "avatar_tattoo_color": None,
        "avatar_tattoo_white_mix": None,
        "OVER": j.AbilityAtual,
        "_url": j.Url,
        "_fm_id": j.FmId,
        "_clube": j.Clube,
    }

    if j.eh_goleiro():
        saida["REF"] = j.Reflexos
        saida["POS"] = j.Posicionamento
        saida["AER"] = j.JogoAereo
        saida["SAI"] = j.SaidaDeBola
        saida["MEN"] = j.Mental
    else:
        saida["TEC"] = j.Tecnica
        saida["ATA"] = j.Ataque
        saida["DEF"] = j.Defesa
        saida["FIS"] = j.Fisico
        saida["MEN"] = j.Mental

    return saida


def agrupar_por_clube(jogadores: Iterable[Jogador]) -> dict[str, list[dict]]:
    grupos: dict[str, list[dict]] = {}
    for j in jogadores:
        slug = slugify(j.Clube or "sem_clube")
        grupos.setdefault(slug, []).append(jogador_para_gofoot(j))
    return grupos


def salvar_jsons_por_clube(
    jogadores: list[Jogador],
    dest_dir: Path,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    caminhos: list[Path] = []
    for slug, lista in agrupar_por_clube(jogadores).items():
        path = dest_dir / f"{slug}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(lista, fh, ensure_ascii=False, indent=2)
        caminhos.append(path)
    return sorted(caminhos)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name
