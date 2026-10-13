"""Demo Streamlit del motor de triaje.  Lanzar con: make app"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from triage.engine import TriageEngine

RAIZ = Path(__file__).resolve().parent
CLIENTES = {p.stem: p for p in sorted((RAIZ / "configs").glob("*.yaml"))}  # cliente nuevo = YAML nuevo
ETIQUETAS_EJEMPLO = {"claro": "Caso claro", "ambiguo": "Caso ambiguo", "pii": "Muchos datos personales"}

st.set_page_config(page_title="Iberianbots · Motor de triaje", layout="wide")


@st.cache_resource
def cargar_motor(cliente: str) -> TriageEngine:
    return TriageEngine.from_config(CLIENTES[cliente], model_dir=RAIZ / "models", log_dir=RAIZ / "logs")


st.title("Motor de triaje de solicitudes")
cliente = st.sidebar.selectbox("Cliente", list(CLIENTES))
motor = cargar_motor(cliente)
st.sidebar.markdown(f"**{motor.config['nombre']}**")
st.sidebar.markdown(f"Umbral de confianza: `{motor.umbral}`")
st.sidebar.markdown("Categorías:\n" + "\n".join(f"- `{c}`" for c in motor.categorias))

if motor.clasificador is None:
    st.error("No hay modelo entrenado para este cliente. Ejecuta `make data train eval`.")
    st.stop()

col_triaje, col_metricas = st.columns([3, 2], gap="large")

# ------------------------------------------------------------------ triaje
with col_triaje:
    st.subheader("Solicitud entrante")
    ejemplos = motor.config.get("ejemplos", {})
    clave_texto = f"texto_{cliente}"
    st.session_state.setdefault(clave_texto, ejemplos.get("claro", ""))
    botones = st.columns(len(ejemplos) or 1)
    for boton, (clave, texto_ejemplo) in zip(botones, ejemplos.items()):
        if boton.button(ETIQUETAS_EJEMPLO.get(clave, clave), use_container_width=True):
            st.session_state[clave_texto] = texto_ejemplo

    texto = st.text_area("Texto", key=clave_texto, height=160, label_visibility="collapsed")

    if texto.strip():
        r = motor.procesar(texto)

        st.markdown("**1 · Texto anonimizado** (lo único que ven el clasificador, el LLM y el registro)")
        st.code(r["texto_anonimizado"], language=None, wrap_lines=True)
        if r["entidades_pii"]:
            st.caption("PII detectada: " + ", ".join(f"{k} × {v}" for k, v in r["entidades_pii"].items()))
        else:
            st.caption("No se ha detectado PII.")

        st.markdown("**2 · Clasificación y enrutado**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Categoría", r["categoria"])
        m2.metric("Confianza", f"{r['confianza']:.0%}")
        m3.metric("Umbral", f"{r['umbral']:.0%}")
        if r["ruta"] == "auto":
            st.success("Decisión: **tramitación automática**")
        else:
            st.warning(f"Decisión: **revisión humana** (segunda opción: `{r['alternativa']}`)")
        st.bar_chart(r["probabilidades"], horizontal=True, height=40 * len(r["probabilidades"]) + 60)

        st.markdown("**3 · Campos extraídos**")
        extraccion = r["extraccion"]
        if extraccion["campos"]:
            st.json(extraccion["campos"])
            st.caption(f"Proveedor LLM: {extraccion['proveedor']}")
        else:
            st.info(extraccion["aviso"])
            st.caption("Campos configurados para esta categoría: "
                       + ", ".join(motor.categorias[r["categoria"]].get("campos", [])))

# ------------------------------------------------------------------ métricas y ROI
with col_metricas:
    st.subheader("Evaluación y ROI")
    ruta_metricas = RAIZ / "reports" / f"{cliente}_metrics.json"
    if not ruta_metricas.exists():
        st.info("Sin métricas todavía. Ejecuta `make eval`.")
    else:
        m = json.loads(ruta_metricas.read_text(encoding="utf-8"))
        a, b = st.columns(2)
        a.metric("Accuracy", f"{m['accuracy']:.1%}")
        b.metric("Macro-F1", f"{m['macro_f1']:.1%}")
        a.metric("Automatizado", f"{m['pct_auto']:.1f}%")
        b.metric("Error en lo automatizado", f"{m['error_auto']:.1f}%")
        st.metric("Horas ahorradas por cada 1.000 solicitudes", f"{m['horas_ahorradas_por_1000']:.0f} h",
                  help="docs automatizados × minutos manuales / 60")
        st.caption(f"Test: {m['n_test']} solicitudes sintéticas · umbral {m['umbral']} · "
                   f"{m['minutos_manuales_por_documento']} min manuales por documento")
        curva = RAIZ / "reports" / f"{cliente}_curva.png"
        if curva.exists():
            st.image(str(curva))
