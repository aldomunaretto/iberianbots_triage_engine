"""Clasificador baseline: TF-IDF (palabras + n-gramas de caracteres) + regresión logística.

Los n-gramas de caracteres dan robustez frente a faltas de ortografía; los de palabras
aportan explicabilidad (se pueden inspeccionar los términos con más peso por categoría).
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


class Clasificador:
    def __init__(self) -> None:
        self.pipeline = Pipeline([
            ("tfidf", FeatureUnion([
                ("palabras", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                             strip_accents="unicode", sublinear_tf=True)),
                ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                                               strip_accents="unicode", sublinear_tf=True)),
            ])),
            ("lr", LogisticRegression(C=10.0, max_iter=2000)),
        ])

    @property
    def categorias(self) -> list[str]:
        return list(self.pipeline.named_steps["lr"].classes_)

    def entrenar(self, textos_anonimizados: list[str], etiquetas: list[str]) -> "Clasificador":
        self.pipeline.fit(textos_anonimizados, etiquetas)
        return self

    def probabilidades(self, textos_anonimizados: list[str]) -> np.ndarray:
        """Matriz (n_textos, n_categorias) con las columnas en el orden de `categorias`."""
        return self.pipeline.predict_proba(textos_anonimizados)

    def guardar(self, ruta: str | Path) -> None:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, ruta)

    @classmethod
    def cargar(cls, ruta: str | Path) -> "Clasificador":
        clf = cls()
        clf.pipeline = joblib.load(ruta)
        return clf
