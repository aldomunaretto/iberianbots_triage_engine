import json

import pytest

from data.generate_synthetic import generar
from triage.engine import TriageEngine
from triage.extractor import extraer_campos
from triage.router import AUTO, REVISION_HUMANA, decidir


@pytest.fixture(scope="module")
def motor(tmp_path_factory):
    """Motor de adminbot entrenado con datos sintéticos en un directorio temporal."""
    tmp = tmp_path_factory.mktemp("triage")
    m = TriageEngine.from_config("configs/adminbot.yaml", model_dir=tmp / "models", log_dir=tmp / "logs")
    df = generar("adminbot", n=120, seed=7)
    return m.entrenar(df["texto"].tolist(), df["etiqueta"].tolist())


def test_flujo_completo(motor):
    r = motor.procesar("Quiero empadronarme, mi DNI es 12345678Z y mi móvil 612345678", extraer=False)
    assert r["categoria"] == "empadronamiento"
    assert r["ruta"] in (AUTO, REVISION_HUMANA)
    assert r["entidades_pii"] == {"DNI": 1, "TELEFONO": 1}
    assert abs(sum(r["probabilidades"].values()) - 1) < 1e-2


def test_el_registro_no_contiene_pii(motor):
    motor.procesar("Queja por la basura. Mi email es vecino@example.com", extraer=False)
    ultima = json.loads(motor.ruta_log.read_text(encoding="utf-8").splitlines()[-1])
    assert "vecino@example.com" not in json.dumps(ultima)
    assert "[EMAIL]" in ultima["texto_anonimizado"]


def test_modelo_se_guarda_y_recarga(motor):
    otro = TriageEngine(motor.config, model_dir=motor.ruta_modelo.parent, log_dir=motor.ruta_log.parent)
    texto = "Solicito licencia de obra menor para reformar la cocina"
    assert otro.procesar(texto, extraer=False, registrar=False)["categoria"] == "licencia_obras"


def test_router_respeta_el_umbral():
    probs = {"a": 0.55, "b": 0.40, "c": 0.05}
    assert decidir(probs, umbral=0.5).ruta == AUTO
    d = decidir(probs, umbral=0.6)
    assert (d.ruta, d.categoria, d.alternativa) == (REVISION_HUMANA, "a", "b")


def test_extractor_sin_clave_no_falla(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = extraer_campos("Recibo del IBI de 300 euros", "tributos", ["tributo", "importe"])
    assert r["campos"] is None and "API_KEY" in r["aviso"]
