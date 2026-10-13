from triage.anonymizer import anonimizar


def test_detecta_todas_las_entidades():
    texto = ("Soy Ana, DNI 12345678Z y NIE X1234567L. Llámame al +34 612 345 678 o al 915551234, "
             "escribe a ana.perez@example.com. Cuenta ES91 2100 0418 4502 0005 1332.")
    anon, recuento = anonimizar(texto)
    assert recuento == {"IBAN": 1, "EMAIL": 1, "NIE": 1, "DNI": 1, "TELEFONO": 2}
    for dato in ["12345678Z", "X1234567L", "612 345 678", "915551234", "ana.perez@example.com", "2100"]:
        assert dato not in anon
    assert "[DNI]" in anon and "[IBAN]" in anon


def test_formatos_alternativos():
    anon, recuento = anonimizar("dni 12345678-z, tlf 699 11 22 33, iban ES7921000813610123456789")
    assert recuento == {"IBAN": 1, "DNI": 1, "TELEFONO": 1}
    assert anon == "dni [DNI], tlf [TELEFONO], iban [IBAN]"


def test_texto_sin_pii_no_cambia():
    texto = "Quiero empadronarme en la calle Mayor 12, pagué 1500 euros en 2026."
    assert anonimizar(texto) == (texto, {})
