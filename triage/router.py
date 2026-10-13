"""Enrutado por confianza: automático si la probabilidad máxima supera el umbral del cliente."""
from __future__ import annotations

from dataclasses import dataclass

AUTO = "auto"
REVISION_HUMANA = "revision_humana"


@dataclass
class Decision:
    categoria: str         # categoría más probable
    confianza: float       # probabilidad de esa categoría
    ruta: str              # "auto" | "revision_humana"
    alternativa: str       # segunda categoría más probable (ayuda al revisor humano)


def decidir(probabilidades: dict[str, float], umbral: float) -> Decision:
    orden = sorted(probabilidades.items(), key=lambda kv: kv[1], reverse=True)
    categoria, confianza = orden[0]
    alternativa = orden[1][0] if len(orden) > 1 else categoria
    ruta = AUTO if confianza >= umbral else REVISION_HUMANA
    return Decision(categoria, float(confianza), ruta, alternativa)
