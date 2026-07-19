from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# Pesos por atributo-chave (estilo FM). Soma ~1.0 por grupo; media_grupo normaliza.
ATTR_TECNICA: dict[str, float] = {
    "Technique": 0.25,
    "Passing": 0.25,
    "First Touch": 0.25,
    "Dribbling": 0.15,
    "Crossing": 0.10,
}
ATTR_ATAQUE: dict[str, float] = {
    "Finishing": 0.25,
    "Off the Ball": 0.25,
    "Composure": 0.25,
    "Long Shots": 0.15,
    "Heading": 0.10,
}
ATTR_DEFESA: dict[str, float] = {
    "Tackling": 0.22,
    "Marking": 0.22,
    "Positioning": 0.22,
    "Aggression": 0.12,
    "Bravery": 0.12,
    "Heading": 0.10,
}
ATTR_FISICO: dict[str, float] = {
    "Acceleration": 0.16,
    "Pace": 0.16,
    "Stamina": 0.16,
    "Strength": 0.16,
    "Agility": 0.12,
    "Balance": 0.12,
    "Jumping Reach": 0.06,
    "Natural Fitness": 0.06,
}
ATTR_MENTAL: dict[str, float] = {
    "Anticipation": 0.15,
    "Decisions": 0.15,
    "Vision": 0.15,
    "Concentration": 0.15,
    "Determination": 0.12,
    "Teamwork": 0.12,
    "Work Rate": 0.12,
    "Flair": 0.04,
}
ATTR_REFLEXOS: dict[str, float] = {
    "Reflexes": 0.65,
    "Handling": 0.35,
}
ATTR_POS_GK: dict[str, float] = {
    "Positioning": 0.40,
    "Command of Area": 0.40,
    "Communication": 0.20,
}
ATTR_AEREO: dict[str, float] = {
    "Aerial Reach": 1.0,
}
ATTR_SAIDA: dict[str, float] = {
    "One on Ones": 0.35,
    "Rushing Out (Tendency)": 0.35,
    "Kicking": 0.15,
    "Throwing": 0.15,
}

POSICAO_FORMULARIO = {
    "GK": "G",
    "DL": "L",
    "DR": "L",
    "WBL": "L",
    "WBR": "L",
    "DC": "Z",
    "DM": "V",
    "MC": "M",
    "AMC": "M",
    "ML": "M",
    "MR": "M",
    "AML": "PE",
    "AMR": "PD",
    "ST": "CA",
}

# Pesos que o Gofoot usa ao recalcular OVER a partir das notas de grupo.
OVER_WEIGHTS = {
    "G": {"REF": 0.20, "POS": 0.20, "AER": 0.20, "SAI": 0.20, "MEN": 0.20},
    "Z": {"TEC": 0.15, "ATA": 0.05, "DEF": 0.40, "FIS": 0.25, "MEN": 0.15},
    "L": {"TEC": 0.25, "ATA": 0.05, "DEF": 0.35, "FIS": 0.20, "MEN": 0.15},
    "V": {"TEC": 0.25, "ATA": 0.05, "DEF": 0.35, "FIS": 0.20, "MEN": 0.15},
    "M": {"TEC": 0.35, "ATA": 0.30, "DEF": 0.05, "FIS": 0.10, "MEN": 0.20},
    "PD": {"TEC": 0.25, "ATA": 0.40, "DEF": 0.05, "FIS": 0.15, "MEN": 0.15},
    "PE": {"TEC": 0.25, "ATA": 0.40, "DEF": 0.05, "FIS": 0.15, "MEN": 0.15},
    "CA": {"TEC": 0.20, "ATA": 0.40, "DEF": 0.05, "FIS": 0.20, "MEN": 0.15},
}

# Mapeamento nota interna → chave de peso OVER.
NOTA_PARA_OVER_KEY = {
    "Tecnica": "TEC",
    "Ataque": "ATA",
    "Defesa": "DEF",
    "Fisico": "FIS",
    "Mental": "MEN",
    "Reflexos": "REF",
    "Posicionamento": "POS",
    "JogoAereo": "AER",
    "SaidaDeBola": "SAI",
}

PE_LETRA = {"Direito": "D", "Esquerdo": "E", "Ambidestro": "A"}


@dataclass
class Jogador:
    Url: str
    Genero: str = ""
    FmId: Optional[int] = None
    Nome: str = ""
    Nacao: str = ""
    Clube: str = ""
    Idade: Optional[int] = None
    PePreferido: str = ""
    Posicoes: str = ""
    Tecnica: Optional[int] = None
    Ataque: Optional[int] = None
    Defesa: Optional[int] = None
    Fisico: Optional[int] = None
    Reflexos: Optional[int] = None
    Posicionamento: Optional[int] = None
    JogoAereo: Optional[int] = None
    SaidaDeBola: Optional[int] = None
    Mental: Optional[int] = None
    Talento: Optional[int] = None
    ValorMercado: Optional[int] = None
    AbilityAtual: Optional[int] = None
    PosicoesFm: str = ""
    Salario: str = ""
    VencimentoContrato: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def posicao_grupo(self) -> Optional[str]:
        primeira = (self.Posicoes or "").split(",")[0].strip().upper()
        return primeira or None

    def eh_goleiro(self) -> bool:
        return self.posicao_grupo() == "G"
