"""Tests de la puerta: cada error de formato que ya se coló una vez es un caso."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from verify import is_guion, validate_script  # noqa: E402

OK = {
    "script": "Uno dos tres. Cuatro cinco seis siete. Ocho nueve diez once. Doce trece.",
    "search_terms": ["a", "b", "c", "d"],
    "character_terms": ["tadeo/x", "*tadeo/y", "", "tadeo/z"],
    "twist_phrase": "Ocho nueve",
}


def test_guion_valido():
    assert validate_script(OK) == []


def test_longitudes_distintas():
    bad = {**OK, "search_terms": ["a", "b", "c"]}
    assert any("search_terms para 4 oraciones" in f for f in validate_script(bad))


def test_character_terms_desparejos():
    bad = {**OK, "character_terms": ["*tadeo/x"]}
    assert any("viajan en paralelo" in f for f in validate_script(bad))


def test_cero_y_dos_beats():
    cero = {**OK, "character_terms": ["a", "b", "c", "d"]}
    dos = {**OK, "character_terms": ["*a", "*b", "c", "d"]}
    assert any("0 beats" in f for f in validate_script(cero))
    assert any("2 beats" in f for f in validate_script(dos))


def test_twist_no_literal_y_fuera_de_banda():
    no_lit = {**OK, "twist_phrase": "ocho nueve"}  # exacto: distingue mayúsculas
    tarde = {**OK, "twist_phrase": "Doce trece"}
    assert any("no aparece literal" in f for f in validate_script(no_lit))
    assert any("banda 25-75" in f for f in validate_script(tarde))


def test_largo_sin_escenas_no_exige_1a1():
    assert validate_script({"script": "Un guion largo. Sin escenas."}) == []


def test_is_guion():
    assert is_guion("scripts/korex-x.json")
    assert not is_guion("scripts/verify.py")
    assert not is_guion("scripts/sub/x.json")
