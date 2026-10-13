"""Orquestador: anonimiza -> clasifica -> enruta -> extrae -> registra.

Todo lo específico de un cliente vive en su YAML; esta clase es idéntica para todos.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from triage.anonymizer import anonimizar
from triage.classifier import Clasificador
from triage.extractor import extraer_campos
from triage.router import decidir


class TriageEngine:
    def __init__(self, config: dict, model_dir: str | Path = "models", log_dir: str | Path = "logs") -> None:
        self.config = config
        self.cliente: str = config["cliente"]
        self.umbral: float = float(config["umbral_confianza"])
        self.categorias: dict = config["categorias"]
        self.ruta_modelo = Path(model_dir) / f"{self.cliente}.joblib"
        self.ruta_log = Path(log_dir) / f"{self.cliente}.jsonl"
        self.clasificador: Clasificador | None = None
        if self.ruta_modelo.exists():
            self.clasificador = Clasificador.cargar(self.ruta_modelo)

    @classmethod
    def from_config(cls, ruta: str | Path, **kwargs) -> "TriageEngine":
        with open(ruta, encoding="utf-8") as f:
            return cls(yaml.safe_load(f), **kwargs)

    # ------------------------------------------------------------ entrenamiento
    def entrenar(self, textos: list[str], etiquetas: list[str], guardar: bool = True) -> "TriageEngine":
        """Entrena sobre texto anonimizado: el modelo nunca ve datos personales."""
        desconocidas = set(etiquetas) - set(self.categorias)
        if desconocidas:
            raise ValueError(f"Etiquetas que no están en el YAML de {self.cliente}: {desconocidas}")
        anonimizados = [anonimizar(t)[0] for t in textos]
        self.clasificador = Clasificador().entrenar(anonimizados, list(etiquetas))
        if guardar:
            self.clasificador.guardar(self.ruta_modelo)
        return self

    # ------------------------------------------------------------ inferencia
    def procesar(self, texto: str, extraer: bool = True, registrar: bool = True) -> dict:
        if self.clasificador is None:
            raise RuntimeError(f"No hay modelo para '{self.cliente}'. Ejecuta `make train` primero.")

        # 1) Anonimización local, antes de cualquier otra cosa
        anonimizado, entidades = anonimizar(texto)

        # 2) Clasificación
        probs = self.clasificador.probabilidades([anonimizado])[0]
        probabilidades = {c: float(p) for c, p in zip(self.clasificador.categorias, probs)}

        # 3) Enrutado por confianza
        decision = decidir(probabilidades, self.umbral)

        # 4) Extracción de campos (opcional, LLM, solo texto anonimizado)
        campos_cfg = self.categorias[decision.categoria].get("campos", [])
        if extraer:
            extraccion = extraer_campos(anonimizado, decision.categoria, campos_cfg)
        else:
            extraccion = {"campos": None, "proveedor": None, "aviso": "Extracción omitida."}

        resultado = {
            "cliente": self.cliente,
            "texto_anonimizado": anonimizado,
            "entidades_pii": entidades,
            "categoria": decision.categoria,
            "confianza": round(decision.confianza, 4),
            "ruta": decision.ruta,
            "alternativa": decision.alternativa,
            "umbral": self.umbral,
            "probabilidades": {c: round(p, 4) for c, p in probabilidades.items()},
            "extraccion": extraccion,
        }

        # 5) Registro (JSONL). Nunca se guarda el texto original.
        if registrar:
            self._registrar(resultado)
        return resultado

    def _registrar(self, resultado: dict) -> None:
        self.ruta_log.parent.mkdir(parents=True, exist_ok=True)
        entrada = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **resultado}
        with open(self.ruta_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
