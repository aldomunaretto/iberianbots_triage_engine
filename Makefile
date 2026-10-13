# Motor de triaje Iberianbots — todo se ejecuta dentro de .venv
PY := .venv/bin/python
CONFIGS := configs/adminbot.yaml configs/lexbot.yaml

.PHONY: setup data train eval app test clean

setup:  ## Crea el entorno virtual e instala dependencias
	python3.13 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt

data:  ## Genera los datasets sintéticos (semilla fija)
	$(PY) data/generate_synthetic.py

train:  ## Entrena un clasificador por cliente (80% de los datos)
	@for c in $(CONFIGS); do $(PY) scripts/train_eval.py --config $$c --solo-entrenar || exit 1; done

eval:  ## Evalúa sobre el 20% reservado y genera reports/
	@for c in $(CONFIGS); do $(PY) scripts/train_eval.py --config $$c --solo-evaluar || exit 1; done

app:  ## Lanza la demo Streamlit
	$(PY) -m streamlit run app.py

test:
	$(PY) -m pytest -q

clean:
	rm -rf models logs data/*.csv reports/*
