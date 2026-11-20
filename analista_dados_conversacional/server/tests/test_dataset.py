from app.eval.dataset import load_dataset
from app.llm.prompts import render
from app.sql_guard.validator import validate


def test_sql_ouro_passa_no_validador():
    checked = 0
    for item in load_dataset():
        golden = item.get("golden_sql")
        if not golden:
            continue
        sql = validate(golden)
        for table in item["tabelas"]:
            assert table in sql
        checked += 1
    assert checked == 17


def test_conjunto_tem_ataque_e_esclarecimento():
    kinds = {item["tipo"] for item in load_dataset()}
    assert kinds == {"consulta", "ataque", "esclarecer"}


def test_prompts_preenchem_os_placeholders():
    text = render(
        "text_to_sql_user.md",
        SCHEMA="schema",
        HISTORY="(sem histórico)",
        QUESTION="Qual o faturamento?",
    )
    assert "schema" in text
    assert "Qual o faturamento?" in text
    assert "<<" not in text
