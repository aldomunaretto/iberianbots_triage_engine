# Evaluación — AdminBot — Ayuntamiento (administración pública)

Datos sintéticos · split 80/20 estratificado (semilla 42) · train=96, test=24

## Resumen

| Métrica | Valor |
|---|---|
| Accuracy | 0.958 |
| Macro-F1 | 0.960 |
| Umbral de confianza configurado | 0.6 |
| % automatizado con ese umbral | 83.3% |
| % error dentro de lo automatizado | 0.0% |
| Entidades PII anonimizadas en test | 42 |

## ROI estimado

ROI = docs automatizados × minutos manuales / 60 = 1.000 × 0.833 × 6 / 60
= **83 horas ahorradas por cada 1.000 solicitudes** (el 16.7% restante va a revisión humana).

## Classification report

```
                 precision    recall  f1-score   support

   ayuda_social      0.833     1.000     0.909         5
empadronamiento      1.000     1.000     1.000         4
 licencia_obras      1.000     1.000     1.000         5
 queja_servicio      1.000     0.800     0.889         5
       tributos      1.000     1.000     1.000         5

       accuracy                          0.958        24
      macro avg      0.967     0.960     0.960        24
   weighted avg      0.965     0.958     0.958        24
```

## Matriz de confusión

| real \ predicho | ayuda_social | empadronamiento | licencia_obras | queja_servicio | tributos |
|---|---|---|---|---|---|
| **ayuda_social** | 5 | 0 | 0 | 0 | 0 |
| **empadronamiento** | 0 | 4 | 0 | 0 | 0 |
| **licencia_obras** | 0 | 0 | 5 | 0 | 0 |
| **queja_servicio** | 1 | 0 | 0 | 4 | 0 |
| **tributos** | 0 | 0 | 0 | 0 | 5 |

## Curva % automatizado vs. error en lo automatizado

![curva](adminbot_curva.png)

| Umbral | % automatizado | % error en lo automatizado | Horas ahorradas / 1.000 |
|---|---|---|---|
| 0.30 | 100.0% | 4.2% | 100 |
| 0.35 | 100.0% | 4.2% | 100 |
| 0.40 | 91.7% | 0.0% | 92 |
| 0.45 | 87.5% | 0.0% | 88 |
| 0.50 | 87.5% | 0.0% | 88 |
| 0.55 | 87.5% | 0.0% | 88 |
| 0.60 | 83.3% | 0.0% | 83 |
| 0.65 | 70.8% | 0.0% | 71 |
| 0.70 | 66.7% | 0.0% | 67 |
| 0.75 | 66.7% | 0.0% | 67 |
| 0.80 | 54.2% | 0.0% | 54 |
| 0.85 | 33.3% | 0.0% | 33 |
| 0.90 | 20.8% | 0.0% | 21 |
| 0.95 | 4.2% | 0.0% | 4 |
