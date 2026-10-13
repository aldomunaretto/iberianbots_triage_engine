"""Genera solicitudes sintéticas en español para cada cliente.

Uso:  python data/generate_synthetic.py [--n 120] [--seed 42]

Cada solicitud se monta con plantillas: saludo + frase(s) de la categoría + datos
personales inventados + despedida. Se añade ruido realista: faltas de ortografía,
tono informal y casos ambiguos que mezclan dos categorías (la etiqueta es la principal).
Todos los datos personales son ficticios.
"""
from __future__ import annotations

import argparse
import random
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent

# ---------------------------------------------------------------- plantillas
PLANTILLAS: dict[str, dict[str, list[str]]] = {
    "adminbot": {
        "empadronamiento": [
            "Quiero empadronarme en el municipio, me acabo de mudar a {direccion}.",
            "Necesito un certificado de empadronamiento para la matrícula del colegio de mi hija.",
            "Solicito el alta en el padrón municipal de habitantes en mi nuevo domicilio de {direccion}.",
            "¿Qué documentos hacen falta para cambiar el domicilio en el padrón?",
            "Necesito el volante de empadronamiento colectivo de todos los que vivimos en el piso.",
            "Solicito la baja del padrón de un antiguo inquilino que ya no reside en mi vivienda.",
            "Me piden un justificante de que estoy empadronado aquí desde hace dos años.",
        ],
        "licencia_obras": [
            "Solicito licencia de obra menor para reformar el baño y la cocina de mi vivienda.",
            "Quiero pedir permiso para cerrar la terraza y cambiar las ventanas en {direccion}.",
            "Necesito saber el estado de mi expediente de licencia de obras para rehabilitar la fachada.",
            "Presento comunicación previa para instalar un andamio y reparar el tejado.",
            "Vamos a construir un garaje en la parcela y necesitamos la licencia urbanística.",
            "¿Hace falta proyecto técnico para tirar un tabique y hacer reforma en el local?",
            "Quiero instalar placas solares en la cubierta, ¿qué permiso de obra necesito?",
        ],
        "queja_servicio": [
            "Quiero poner una queja porque llevan dos semanas sin recoger la basura en mi calle.",
            "Las farolas de la plaza llevan fundidas un mes y nadie hace nada.",
            "Presento una reclamación por el ruido de la limpieza viaria de madrugada.",
            "El autobús urbano nunca pasa a su hora, es una vergüenza de servicio.",
            "Hay un socavón enorme en la acera de {direccion} y ya se ha caído una vecina.",
            "Me atendieron fatal en la oficina de atención ciudadana, quiero dejar constancia de mi malestar.",
            "El parque infantil está lleno de cristales y los columpios rotos, es intolerable.",
        ],
        "ayuda_social": [
            "Solicito información sobre la ayuda de emergencia social, estoy en paro y no llego a fin de mes.",
            "Quiero pedir la ayuda al alquiler para familias con pocos recursos.",
            "Necesito cita con la trabajadora social para tramitar la ayuda a la dependencia de mi madre.",
            "Solicito la beca de comedor escolar para mis dos hijos.",
            "¿Cómo puedo pedir el bono social o alguna prestación económica municipal?",
            "Somos familia numerosa y queremos solicitar la subvención para material escolar.",
            "Mi padre vive solo y necesita el servicio de teleasistencia y ayuda a domicilio.",
        ],
        "tributos": [
            "Me ha llegado el recibo del IBI y creo que el importe de {importe} euros es incorrecto.",
            "Quiero domiciliar el impuesto de vehículos en mi cuenta bancaria.",
            "Solicito fraccionar el pago de la tasa de basuras, son {importe} euros.",
            "Necesito un duplicado del recibo del impuesto de circulación.",
            "Solicito la devolución de la plusvalía municipal que pagué al vender el piso.",
            "¿Hasta cuándo está abierto el plazo voluntario para pagar el IBI sin recargo?",
            "Me han embargado {importe} euros por una tasa que ya estaba pagada.",
        ],
    },
    "lexbot": {
        "demanda": [
            "Quiero interponer una demanda contra mi antiguo casero por no devolverme la fianza de {importe} euros.",
            "Me han notificado una demanda de reclamación de cantidad y necesito contestarla.",
            "Quiero demandar a mi empresa por despido improcedente.",
            "Necesito presentar una demanda de divorcio contencioso.",
            "Un cliente me debe {importe} euros y quiero reclamarlos judicialmente.",
            "Quiero iniciar un procedimiento monitorio contra un moroso.",
            "Mi vecino me ha causado daños por una fuga de agua y quiero llevarlo a juicio.",
        ],
        "contrato": [
            "Necesito que revisen un contrato de arrendamiento antes de firmarlo.",
            "Quiero redactar un contrato de prestación de servicios con un proveedor.",
            "¿Pueden revisar las cláusulas de mi contrato de trabajo? Hay una de no competencia.",
            "Necesito un contrato de compraventa para vender mi vehículo.",
            "Queremos redactar un acuerdo de confidencialidad con un socio.",
            "Quiero rescindir el contrato de alquiler del local y no sé qué penalización tiene.",
            "Me ofrecen un pacto de socios y quiero que alguien revise las condiciones.",
        ],
        "recurso": [
            "Quiero recurrir una multa de tráfico que me parece injusta.",
            "Necesito presentar recurso de apelación contra la sentencia del juzgado.",
            "Me han denegado la prestación y quiero interponer recurso de alzada.",
            "Quiero recurrir la resolución de Hacienda, el plazo acaba el {fecha}.",
            "Hemos perdido en primera instancia y queremos apelar.",
            "Necesito preparar un recurso de reposición contra una sanción administrativa.",
            "Me han desestimado la reclamación y quiero impugnar esa resolución.",
        ],
        "poder_notarial": [
            "Necesito otorgar un poder notarial a mi hermano para que venda un piso en mi nombre.",
            "Quiero hacer un poder general para pleitos a favor de mi abogado.",
            "¿Qué necesito para dar un poder a mi hija para gestionar mis cuentas?",
            "Vivo en el extranjero y necesito apoderar a un familiar para aceptar una herencia.",
            "Quiero revocar el poder notarial que otorgué a mi expareja.",
            "Necesito un poder preventivo por si en el futuro no puedo valerme por mí mismo.",
            "Mi madre quiere nombrarme apoderado ante notario para sus gestiones.",
        ],
    },
}

SALUDOS_FORMALES = ["Buenos días.", "Buenas tardes.", "Estimados señores:", "A quien corresponda:", ""]
SALUDOS_INFORMALES = ["hola!!", "buenas", "holaa, a ver si me podeis ayudar", "ey buenas tardes", "oye una cosa"]
DESPEDIDAS_FORMALES = ["Gracias de antemano.", "Quedo a la espera de su respuesta.", "Un saludo.", "Atentamente.", ""]
DESPEDIDAS_INFORMALES = ["gracias!!", "a ver si me decis algo pronto", "un saludo", "porfa es urgente", ""]
NEXOS_AMBIGUOS = ["Además,", "Y de paso,", "Por otro lado,", "Aprovecho también porque", "Ah, y otra cosa:"]

NOMBRES = ["María García", "Antonio López", "Carmen Ruiz", "José Martínez", "Lucía Fernández",
           "Javier Ortega", "Ana Belén Soto", "Mohamed El Idrissi", "Elena Popescu", "Pablo Navarro"]
CALLES = ["calle Mayor 12", "avenida de la Constitución 45, 3ºB", "plaza del Carmen 3",
          "calle Real 78", "paseo de la Estación 9", "calle San Roque 21, bajo"]
LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


# ---------------------------------------------------------------- datos personales ficticios
def dni(rng: random.Random) -> str:
    n = rng.randint(10_000_000, 99_999_999)
    sep = rng.choice(["", "", "-"])
    return f"{n}{sep}{LETRAS_DNI[n % 23]}"


def nie(rng: random.Random) -> str:
    return f"{rng.choice('XYZ')}{rng.randint(1_000_000, 9_999_999)}{rng.choice(LETRAS_DNI)}"


def telefono(rng: random.Random) -> str:
    d = f"{rng.choice('679')}{rng.randint(10_000_000, 99_999_999)}"
    return rng.choice([
        d,
        f"{d[:3]} {d[3:6]} {d[6:]}",
        f"{d[:3]} {d[3:5]} {d[5:7]} {d[7:]}",
        f"+34 {d[:3]} {d[3:6]} {d[6:]}",
        f"+34{d}",
    ])


def email(rng: random.Random, nombre: str) -> str:
    usuario = quitar_tildes(nombre).lower().replace(" ", rng.choice([".", "_", ""]))
    return f"{usuario}{rng.randint(1, 99)}@{rng.choice(['gmail.com', 'hotmail.es', 'yahoo.es', 'outlook.com'])}"


def iban(rng: random.Random) -> str:
    d = "".join(str(rng.randint(0, 9)) for _ in range(22))
    crudo = "ES" + d
    return rng.choice([crudo, " ".join(crudo[i:i + 4] for i in range(0, 24, 4))])


def frase_pii(rng: random.Random) -> str:
    """Devuelve 0-3 frases con datos personales inventados."""
    nombre = rng.choice(NOMBRES)
    opciones = [
        f"Mi nombre es {nombre} y mi DNI es {dni(rng)}.",
        f"Soy {nombre}, con NIE {nie(rng)}.",
        f"Mi teléfono de contacto es el {telefono(rng)}.",
        f"Pueden escribirme a {email(rng, nombre)}.",
        f"El número de cuenta es {iban(rng)}.",
        f"Me pueden llamar al {telefono(rng)} o mandar un correo a {email(rng, nombre)}.",
    ]
    return " ".join(rng.sample(opciones, k=rng.choice([0, 1, 1, 2, 2, 3])))


# ---------------------------------------------------------------- ruido
def quitar_tildes(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn" or c == "̃")  # conserva la ñ


def meter_faltas(texto: str, rng: random.Random, prob: float = 0.12) -> str:
    """Faltas típicas: sin tildes, sin h, b/v, letras bailadas u omitidas."""
    palabras = []
    for p in quitar_tildes(texto).split():
        # No tocamos tokens con dígitos o '@' para no romper los datos personales
        if len(p) > 4 and p.isalpha() and rng.random() < prob:
            tipo = rng.choice(["swap", "drop", "bv", "h"])
            i = rng.randint(1, len(p) - 2)
            if tipo == "swap":
                p = p[:i] + p[i + 1] + p[i] + p[i + 2:]
            elif tipo == "drop":
                p = p[:i] + p[i + 1:]
            elif tipo == "bv":
                p = p.replace("b", "v", 1) if "b" in p else p.replace("v", "b", 1)
            elif tipo == "h" and p.lower().startswith("h"):
                p = p[1:]
        palabras.append(p)
    return " ".join(palabras)


# ---------------------------------------------------------------- generación
def rellenar(frase: str, rng: random.Random) -> str:
    return frase.format(
        direccion=rng.choice(CALLES),
        importe=rng.choice([85, 120, 349, 612, 1500, 2300]),
        fecha=f"{rng.randint(1, 28)}/{rng.randint(1, 12)}/2026",
    )


def generar(cliente: str, n: int = 120, seed: int = 42) -> pd.DataFrame:
    """Genera n solicitudes etiquetadas para un cliente. Determinista dada la semilla."""
    rng = random.Random(f"{cliente}-{seed}")
    plantillas = PLANTILLAS[cliente]
    categorias = list(plantillas)
    filas = []
    for i in range(n):
        etiqueta = categorias[i % len(categorias)]  # clases equilibradas
        informal = rng.random() < 0.35
        ambiguo = rng.random() < 0.15

        cuerpo = rellenar(rng.choice(plantillas[etiqueta]), rng)
        if ambiguo:
            otra = rng.choice([c for c in categorias if c != etiqueta])
            cuerpo += f" {rng.choice(NEXOS_AMBIGUOS)} {rellenar(rng.choice(plantillas[otra]), rng).lower()}"

        saludo = rng.choice(SALUDOS_INFORMALES if informal else SALUDOS_FORMALES)
        despedida = rng.choice(DESPEDIDAS_INFORMALES if informal else DESPEDIDAS_FORMALES)
        texto = " ".join(t for t in [saludo, cuerpo, frase_pii(rng), despedida] if t)

        if informal:
            texto = meter_faltas(texto, rng).lower() if rng.random() < 0.5 else meter_faltas(texto, rng)
        elif rng.random() < 0.2:
            texto = meter_faltas(texto, rng, prob=0.06)

        filas.append({"texto": texto, "etiqueta": etiqueta, "ambiguo": int(ambiguo)})
    return pd.DataFrame(filas).sample(frac=1, random_state=seed).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    for cliente in PLANTILLAS:
        df = generar(cliente, args.n, args.seed)
        salida = RAIZ / f"{cliente}.csv"
        df.to_csv(salida, index=False)
        print(f"[data] {cliente}: {len(df)} solicitudes ({df['ambiguo'].sum()} ambiguas) -> {salida}")


if __name__ == "__main__":
    main()
