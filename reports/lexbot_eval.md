# Evaluación — LexBot — Despacho de abogados

Datos sintéticos · split 80/20 estratificado (semilla 42) · train=96, test=24

## Resumen

| Métrica | Valor |
|---|---|
| Accuracy | 0.917 |
| Macro-F1 | 0.916 |
| Umbral de confianza configurado | 0.75 |
| % automatizado con ese umbral | 66.7% |
| % error dentro de lo automatizado | 0.0% |
| Entidades PII anonimizadas en test | 40 |

## ROI estimado

ROI = docs automatizados × minutos manuales / 60 = 1.000 × 0.667 × 9 / 60
= **100 horas ahorradas por cada 1.000 solicitudes** (el 33.3% restante va a revisión humana).

## Classification report

```
                precision    recall  f1-score   support

      contrato      0.833     0.833     0.833         6
       demanda      0.857     1.000     0.923         6
poder_notarial      1.000     0.833     0.909         6
       recurso      1.000     1.000     1.000         6

      accuracy                          0.917        24
     macro avg      0.923     0.917     0.916        24
  weighted avg      0.923     0.917     0.916        24
```

## Matriz de confusión

| real \ predicho | contrato | demanda | poder_notarial | recurso |
|---|---|---|---|---|
| **contrato** | 5 | 1 | 0 | 0 |
| **demanda** | 0 | 6 | 0 | 0 |
| **poder_notarial** | 1 | 0 | 5 | 0 |
| **recurso** | 0 | 0 | 0 | 6 |

## Curva % automatizado vs. error en lo automatizado

![curva](lexbot_curva.png)

| Umbral | % automatizado | % error en lo automatizado | Horas ahorradas / 1.000 |
|---|---|---|---|
| 0.30 | 100.0% | 8.3% | 150 |
| 0.35 | 100.0% | 8.3% | 150 |
| 0.40 | 100.0% | 8.3% | 150 |
| 0.45 | 100.0% | 8.3% | 150 |
| 0.50 | 95.8% | 8.7% | 144 |
| 0.55 | 95.8% | 8.7% | 144 |
| 0.60 | 87.5% | 4.8% | 131 |
| 0.65 | 79.2% | 5.3% | 119 |
| 0.70 | 70.8% | 0.0% | 106 |
| 0.75 | 66.7% | 0.0% | 100 |
| 0.80 | 66.7% | 0.0% | 100 |
| 0.85 | 58.3% | 0.0% | 88 |
| 0.90 | 45.8% | 0.0% | 69 |
| 0.95 | 29.2% | 0.0% | 44 |
