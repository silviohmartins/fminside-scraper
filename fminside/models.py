from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


ATTR_TECNICA = ("Technique", "First Touch", "Dribbling", "Passing", "Crossing")
ATTR_ATAQUE = ("Finishing", "Long Shots", "Heading", "Off the Ball", "Composure")
ATTR_DEFESA = ("Tackling", "Marking", "Positioning", "Heading", "Aggression", "Bravery")
ATTR_FISICO = (
    "Acceleration",
    "Pace",
    "Stamina",
    "Strength",
    "Agility",
    "Balance",
    "Jumping Reach",
    "Natural Fitness",
)
ATTR_MENTAL = (
    "Anticipation",
    "Decisions",
    "Concentration",
    "Determination",
    "Vision",
    "Teamwork",
    "Work Rate",
    "Flair",
)
ATTR_REFLEXOS = ("Reflexes", "Handling")
ATTR_POS_GK = ("Command of Area", "Communication", "Positioning")
ATTR_AEREO = ("Aerial Reach",)
ATTR_SAIDA = ("Kicking", "Throwing", "Rushing Out (Tendency)", "One on Ones")

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

    def calcular_overall(self) -> Optional[int]:
        grupo = self.posicao_grupo()
        pesos = OVER_WEIGHTS.get(grupo or "")
        if not pesos:
            return None
        if self.eh_goleiro():
            valores = {
                "REF": self.Reflexos,
                "POS": self.Posicionamento,
                "AER": self.JogoAereo,
                "SAI": self.SaidaDeBola,
                "MEN": self.Mental,
            }
        else:
            valores = {
                "TEC": self.Tecnica,
                "ATA": self.Ataque,
                "DEF": self.Defesa,
                "FIS": self.Fisico,
                "MEN": self.Mental,
            }
        total = 0.0
        for chave, peso in pesos.items():
            v = valores.get(chave)
            if v is None:
                return None
            total += float(v) * peso
        return int(round(total))
