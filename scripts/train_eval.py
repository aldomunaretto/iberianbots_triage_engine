"""Entrena y evalúa el clasificador de un cliente.

Uso:  python scripts/train_eval.py --config configs/adminbot.yaml [--solo-entrenar | --solo-evaluar]

Split 80/20 estratificado con semilla fija (entrenar y evaluar por separado usan el mismo corte).
Genera reports/<cliente>_eval.md, reports/<cliente>_curva.png y reports/<cliente>_metrics.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # sin ventana: solo guardamos el PNG
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

from triage.anonymizer import anonimizar  # noqa: E402
from triage.engine import TriageEngine  # noqa: E402

SEMILLA = 42
UMBRALES = np.round(np.arange(0.30, 0.951, 0.05), 2)


def curva_automatizacion(confianza: np.ndarray, acierto: np.ndarray) -> list[dict]:
    """Para cada umbral: % de solicitudes automatizadas y % de error dentro de ellas."""
    filas = []
    for u in UMBRALES:
        auto = confianza >= u
        filas.append({
            "umbral": float(u),
            "pct_auto": float(auto.mean() * 100),
            "error_auto": float((~acierto[auto]).mean() * 100) if auto.any() else 0.0,
        })
    return filas


def roi_horas_por_1000(pct_auto: float, minutos: float) -> float:
    """ROI = docs automatizados × minutos manuales / 60, por cada 1.000 solicitudes."""
    return 1000 * (pct_auto / 100) * minutos / 60


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    grupo = ap.add_mutually_exclusive_group()
    grupo.add_argument("--solo-entrenar", action="store_true")
    grupo.add_argument("--solo-evaluar", action="store_true")
    args = ap.parse_args()

    motor = TriageEngine.from_config(args.config, model_dir=RAIZ / "models", log_dir=RAIZ / "logs")
    cfg, cliente = motor.config, motor.cliente
    df = pd.read_csv(RAIZ / cfg["datos"])
    train, test = train_test_split(df, test_size=0.2, stratify=df["etiqueta"], random_state=SEMILLA)

    if not args.solo_evaluar:
        motor.entrenar(train["texto"].tolist(), train["etiqueta"].tolist())
        print(f"[train] {cliente}: {len(train)} ejemplos -> {motor.ruta_modelo.relative_to(RAIZ)}")
        if args.solo_entrenar:
            return
    if motor.clasificador is None:
        sys.exit(f"No existe {motor.ruta_modelo}. Ejecuta primero `make train`.")

    # ---------------------------------------------------------- evaluación
    anonimizados, n_pii = [], 0
    for t in test["texto"]:
        anon, entidades = anonimizar(t)
        anonimizados.append(anon)
        n_pii += sum(entidades.values())

    etiquetas = motor.clasificador.categorias
    probs = motor.clasificador.probabilidades(anonimizados)
    pred = np.array(etiquetas)[probs.argmax(axis=1)]
    confianza = probs.max(axis=1)
    y = test["etiqueta"].to_numpy()
    acierto = pred == y

    acc = accuracy_score(y, pred)
    f1 = f1_score(y, pred, average="macro")
    informe = classification_report(y, pred, digits=3, zero_division=0)
    matriz = confusion_matrix(y, pred, labels=etiquetas)
    curva = curva_automatizacion(confianza, acierto)

    umbral, minutos = motor.umbral, cfg["minutos_manuales_por_documento"]
    auto = confianza >= umbral
    pct_auto = float(auto.mean() * 100)
    error_auto = float((~acierto[auto]).mean() * 100) if auto.any() else 0.0
    horas = roi_horas_por_1000(pct_auto, minutos)

    print(f"\n===== {cfg['nombre']} — test n={len(test)} =====")
    print(informe)
    print("Matriz de confusión (filas=real, columnas=predicho):")
    print(pd.DataFrame(matriz, index=etiquetas, columns=etiquetas).to_string())
    print(f"\nUmbral {umbral}: {pct_auto:.1f}% automatizado, {error_auto:.1f}% de error en lo automatizado, "
          f"{horas:.0f} h ahorradas por cada 1.000 solicitudes")

    # ---------------------------------------------------------- gráfico
    reports = RAIZ / "reports"
    reports.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([c["umbral"] for c in curva], [c["pct_auto"] for c in curva], marker="o", label="% automatizado")
    ax.plot([c["umbral"] for c in curva], [c["error_auto"] for c in curva], marker="s",
            label="% error en lo automatizado")
    ax.axvline(umbral, color="gray", linestyle="--", linewidth=1, label=f"umbral configurado ({umbral})")
    ax.set(xlabel="Umbral de confianza", ylabel="% de solicitudes", ylim=(0, 105),
           title=f"{cliente}: automatización vs. error (test n={len(test)})")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(reports / f"{cliente}_curva.png", dpi=130)
    plt.close(fig)

    # ---------------------------------------------------------- informe markdown + json
    metricas = {
        "cliente": cliente, "n_train": len(train), "n_test": len(test),
        "accuracy": round(acc, 4), "macro_f1": round(f1, 4), "umbral": umbral,
        "pct_auto": round(pct_auto, 1), "error_auto": round(error_auto, 1),
        "minutos_manuales_por_documento": minutos, "horas_ahorradas_por_1000": round(horas, 1),
        "entidades_pii_en_test": n_pii, "curva": curva,
    }
    (reports / f"{cliente}_metrics.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False))

    cabecera = "| real \\ predicho | " + " | ".join(etiquetas) + " |\n|---|" + "---|" * len(etiquetas)
    filas_matriz = "\n".join(f"| **{e}** | " + " | ".join(map(str, fila)) + " |" for e, fila in zip(etiquetas, matriz))
    filas_curva = "\n".join(
        f"| {c['umbral']:.2f} | {c['pct_auto']:.1f}% | {c['error_auto']:.1f}% | "
        f"{roi_horas_por_1000(c['pct_auto'], minutos):.0f} |" for c in curva)
    md = f"""# Evaluación — {cfg['nombre']}

Datos sintéticos · split 80/20 estratificado (semilla {SEMILLA}) · train={len(train)}, test={len(test)}

## Resumen

| Métrica | Valor |
|---|---|
| Accuracy | {acc:.3f} |
| Macro-F1 | {f1:.3f} |
| Umbral de confianza configurado | {umbral} |
| % automatizado con ese umbral | {pct_auto:.1f}% |
| % error dentro de lo automatizado | {error_auto:.1f}% |
| Entidades PII anonimizadas en test | {n_pii} |

## ROI estimado

ROI = docs automatizados × minutos manuales / 60 = 1.000 × {pct_auto / 100:.3f} × {minutos} / 60
= **{horas:.0f} horas ahorradas por cada 1.000 solicitudes** (el {100 - pct_auto:.1f}% restante va a revisión humana).

## Classification report

```
{informe}```

## Matriz de confusión

{cabecera}
{filas_matriz}

## Curva % automatizado vs. error en lo automatizado

![curva]({cliente}_curva.png)

| Umbral | % automatizado | % error en lo automatizado | Horas ahorradas / 1.000 |
|---|---|---|---|
{filas_curva}
"""
    (reports / f"{cliente}_eval.md").write_text(md, encoding="utf-8")
    print(f"[eval] informe -> reports/{cliente}_eval.md, reports/{cliente}_curva.png")


if __name__ == "__main__":
    main()
