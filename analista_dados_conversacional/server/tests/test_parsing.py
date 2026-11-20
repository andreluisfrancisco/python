import pytest

from app.llm.parsing import ModelFormatError, parse_model_json


def test_json_com_cerca():
    payload = parse_model_json('```json\n{"intent": "query", "sql": "SELECT 1"}\n```')
    assert payload["intent"] == "query"


def test_json_com_texto_em_volta():
    payload = parse_model_json('Segue o plano:\n{"intent": "clarify", "message": "Qual período?"}')
    assert payload["message"] == "Qual período?"


def test_json_invalido():
    with pytest.raises(ModelFormatError):
        parse_model_json("não é json")
