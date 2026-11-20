from app.conversation.history import render_history


def test_historico_vazio():
    assert render_history([], max_messages=4) == "(sem histórico)"


def test_corta_o_mais_antigo_e_nao_comeca_em_resposta():
    messages = [
        {"role": "user", "content": "primeira"},
        {"role": "assistant", "content": "resposta 1", "sql": "SELECT 1 FROM analista.clientes"},
        {"role": "user", "content": "segunda"},
        {"role": "assistant", "content": "resposta 2", "sql": None},
    ]
    text = render_history(messages, max_messages=2)
    assert "primeira" not in text
    assert text.startswith("Usuário: segunda")
    assert "Analista: resposta 2" in text


def test_trunca_texto_longo():
    text = render_history([{"role": "user", "content": "a" * 800}], max_messages=4, max_chars=20)
    assert "…" in text
    assert "a" * 30 not in text
