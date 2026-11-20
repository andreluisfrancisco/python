import pytest

from app.sql_guard.validator import SqlRejected, validate


def test_select_simples_recebe_limite():
    sql = validate("SELECT nome FROM analista.clientes")
    assert sql.endswith("LIMIT 200")
    assert "analista.clientes" in sql


def test_limit_alto_e_rebaixado():
    sql = validate("SELECT nome FROM analista.clientes LIMIT 5000")
    assert "LIMIT 200" in sql
    assert "5000" not in sql


def test_limit_baixo_permanece():
    sql = validate("SELECT nome FROM analista.clientes LIMIT 10")
    assert sql.endswith("LIMIT 10")


def test_limit_interno_nao_impede_o_limite_externo():
    sql = validate("SELECT * FROM (SELECT nome FROM analista.clientes LIMIT 1) s")
    assert sql.endswith("LIMIT 200")


def test_cte_e_aceita():
    sql = validate(
        "WITH ativos AS (SELECT id FROM analista.clientes) SELECT * FROM ativos"
    )
    assert "ativos" in sql.lower()


def test_extract_nao_vira_tabela():
    validate("SELECT EXTRACT(MONTH FROM p.criado_em) AS mes FROM analista.pedidos p")


def test_filtro_com_palavra_perigosa_dentro_de_texto():
    validate("SELECT nome FROM analista.clientes WHERE nome = 'drop table'")


def test_empilhamento_e_recusado():
    with pytest.raises(SqlRejected):
        validate("SELECT nome FROM analista.clientes; DROP TABLE analista.clientes")


def test_comentario_com_segundo_comando_e_recusado():
    with pytest.raises(SqlRejected):
        validate("SELECT nome FROM analista.clientes --\n; DROP TABLE analista.pedidos")


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO analista.clientes (id, nome) VALUES (1, 'a')",
        "UPDATE analista.clientes SET nome = 'a'",
        "DELETE FROM analista.clientes",
        "DROP TABLE analista.clientes",
        "SELECT pg_sleep(10)",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM analista.usuarios",
        "SELECT nome INTO TEMP TABLE copia FROM analista.clientes",
        "SELECT * FROM analista.clientes FOR UPDATE",
        "",
    ],
)
def test_comandos_perigosos(sql):
    with pytest.raises(SqlRejected):
        validate(sql)


def test_offset_permanece_quando_o_limite_e_cortado():
    sql = validate("SELECT nome FROM analista.clientes ORDER BY nome LIMIT 999 OFFSET 5")
    assert "LIMIT 200" in sql
    assert "OFFSET 5" in sql
