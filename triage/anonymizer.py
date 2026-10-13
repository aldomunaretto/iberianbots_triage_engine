"""Anonimización local de datos personales (PII) mediante expresiones regulares.

Se ejecuta SIEMPRE antes de entrenar, clasificar o llamar a un LLM: ningún dato
personal detectado sale de la máquina. Cubre DNI, NIE, teléfono español, email e IBAN.
"""
from __future__ import annotations

import re

# El orden importa: primero los patrones más largos/específicos (un IBAN contiene
# secuencias de dígitos que podrían confundirse con un teléfono o un DNI).
PATRONES: list[tuple[str, re.Pattern[str]]] = [
    ("IBAN", re.compile(r"\bES\d{2}(?:[ -]?\d{4}){5}\b", re.IGNORECASE)),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("NIE", re.compile(r"\b[XYZ][ -]?\d{7}[ -]?[A-Z]\b", re.IGNORECASE)),
    ("DNI", re.compile(r"\b\d{8}[ -]?[A-Z]\b", re.IGNORECASE)),
    # Prefijo opcional +34/0034 y 9 dígitos que empiezan por 6-9, con separadores libres
    ("TELEFONO", re.compile(r"(?<![\w+])(?:(?:\+|00)34[ .-]?)?[6-9](?:[ .-]?\d){8}(?!\d)")),
]


def anonimizar(texto: str) -> tuple[str, dict[str, int]]:
    """Sustituye cada entidad por su etiqueta ([DNI], [TELEFONO]...).

    Devuelve el texto anonimizado y el recuento de entidades detectadas por tipo.
    """
    recuento: dict[str, int] = {}
    for etiqueta, patron in PATRONES:
        texto, n = patron.subn(f"[{etiqueta}]", texto)
        if n:
            recuento[etiqueta] = n
    return texto, recuento
