"""Extracción opcional de campos con un LLM (Anthropic u OpenAI).

Solo recibe texto YA anonimizado. Si no hay clave de API (o falla la llamada) devuelve
un aviso en lugar de lanzar una excepción: el triaje funciona igual sin LLM.
"""
from __future__ import annotations

import os

from pydantic import BaseModel, ValidationError, create_model

MODELO_ANTHROPIC = os.getenv("TRIAGE_ANTHROPIC_MODEL", "claude-opus-5-5")
MODELO_OPENAI = os.getenv("TRIAGE_OPENAI_MODEL", "gpt-4o-mini")

INSTRUCCIONES = (
    "Eres un asistente que extrae datos de solicitudes en español. El texto está anonimizado: "
    "las etiquetas como [DNI] o [TELEFONO] sustituyen a datos personales y no deben interpretarse. "
    "Extrae los campos pedidos para una solicitud de la categoría '{categoria}'. "
    "Si un campo no aparece en el texto, devuelve null. No inventes información.\n\n"
    "Campos: {campos}\n\nSolicitud:\n{texto}"
)


def modelo_campos(categoria: str, campos: list[str]) -> type[BaseModel]:
    """Crea al vuelo un modelo Pydantic con los campos que el YAML define para la categoría."""
    definicion = {campo: (str | None, ...) for campo in campos}
    return create_model(f"Campos_{categoria}", **definicion)


def extraer_campos(texto_anonimizado: str, categoria: str, campos: list[str]) -> dict:
    """Devuelve {"campos": {...}|None, "proveedor": str|None, "aviso": str|None}."""
    if not campos:
        return {"campos": {}, "proveedor": None, "aviso": None}

    Modelo = modelo_campos(categoria, campos)
    prompt = INSTRUCCIONES.format(categoria=categoria, campos=", ".join(campos), texto=texto_anonimizado)

    try:
        if os.getenv("ANTHROPIC_API_KEY"):
            return {"campos": _con_anthropic(prompt, Modelo), "proveedor": "anthropic", "aviso": None}
        if os.getenv("OPENAI_API_KEY"):
            return {"campos": _con_openai(prompt, Modelo), "proveedor": "openai", "aviso": None}
    except ValidationError as e:
        return {"campos": None, "proveedor": None, "aviso": f"El LLM devolvió un JSON no válido: {e.error_count()} errores."}
    except Exception as e:  # red, cuota, SDK no instalado... nunca tumbamos el triaje
        return {"campos": None, "proveedor": None, "aviso": f"Extracción no disponible ({type(e).__name__}: {e})"}

    return {
        "campos": None,
        "proveedor": None,
        "aviso": "Extracción desactivada: define ANTHROPIC_API_KEY u OPENAI_API_KEY para activarla.",
    }


def _con_anthropic(prompt: str, Modelo: type[BaseModel]) -> dict:
    import anthropic  # import perezoso: el motor no depende del SDK si no hay clave

    respuesta = anthropic.Anthropic().messages.parse(
        model=MODELO_ANTHROPIC,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
        output_format=Modelo,  # salida estructurada: el SDK valida contra el modelo Pydantic
    )
    if respuesta.parsed_output is None:
        raise RuntimeError(f"respuesta sin salida estructurada (stop_reason={respuesta.stop_reason})")
    return respuesta.parsed_output.model_dump()


def _con_openai(prompt: str, Modelo: type[BaseModel]) -> dict:
    from openai import OpenAI  # opcional: pip install openai

    respuesta = OpenAI().chat.completions.create(
        model=MODELO_OPENAI,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt + "\n\nResponde solo con un objeto JSON con esos campos."}],
    )
    return Modelo.model_validate_json(respuesta.choices[0].message.content).model_dump()
