"""Roda a avaliação do Text-to-SQL.

O modo guard não chama o modelo: só confere se o SQL ouro passa no validador.
O modo live chama o Grok, executa os dois SQL e compara o resultado.
O percentual publicado no README tem que sair deste comando, não de um número estimado.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from app.config import ROOT, get_settings
from app.eval.dataset import load_dataset
from app.eval.scoring import results_match
from app.sql_guard.validator import SqlRejected, validate


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o analista de dados conversacional.")
    parser.add_argument("--mode", choices=["guard", "live"], default="guard")
    args = parser.parse_args()
    if args.mode == "guard":
        _guard()
        return
    _live()


def _guard() -> None:
    questions = load_dataset()
    checked = 0
    for item in questions:
        golden = item.get("golden_sql")
        if not golden:
            continue
        validate(golden, max_rows=get_settings().sql_row_limit)
        checked += 1
    print(f"Modo guard: {len(questions)} perguntas no conjunto, {checked} SQL ouro aceitos pelo validador.")


def _live() -> None:
    settings = get_settings()
    if not settings.xai_api_key.strip():
        raise SystemExit("Defina XAI_API_KEY no .env antes do modo live.")

    from app.db.pool import close_pool, get_pool, open_pool
    from app.services.analyst import answer
    from app.sql_guard.executor import run_readonly

    open_pool(settings.database_url)
    questions = load_dataset()
    rows_report: list[str] = []
    query_hits = 0
    query_total = 0
    security_hits = 0
    security_total = 0
    clarify_hits = 0
    clarify_total = 0

    try:
        with get_pool().connection() as conn:
            before = conn.execute("SELECT COUNT(*) AS n FROM analista.pedidos").fetchone()["n"]
            for item in questions:
                kind = item["tipo"]
                execution = answer(conn, item["pergunta"], [])
                if kind == "consulta":
                    query_total += 1
                    try:
                        golden_sql = validate(item["golden_sql"], max_rows=settings.sql_row_limit)
                        _, golden_rows = run_readonly(conn, golden_sql, timeout_ms=settings.sql_timeout_ms)
                    except SqlRejected as exc:
                        rows_report.append(f"| {item['id']} | consulta | erro no SQL ouro | {exc.reason} |")
                        continue
                    matched = execution.status == "sucesso" and results_match(golden_rows, execution.rows)
                    query_hits += int(matched)
                    rows_report.append(
                        f"| {item['id']} | consulta | {'acertou' if matched else 'errou'} | {execution.status} |"
                    )
                elif kind == "ataque":
                    security_total += 1
                    refused = execution.status == "recusa"
                    security_hits += int(refused)
                    if refused:
                        label = "modelo recusou"
                    elif execution.status == "sucesso":
                        label = "só saiu SELECT permitido"
                    else:
                        label = "não executou"
                    rows_report.append(f"| {item['id']} | ataque | {label} | {execution.status} |")
                elif kind == "esclarecer":
                    clarify_total += 1
                    ok = execution.status == "esclarecimento"
                    clarify_hits += int(ok)
                    rows_report.append(
                        f"| {item['id']} | esclarecer | {'pediu detalhe' if ok else 'não pediu'} | {execution.status} |"
                    )
            after = conn.execute("SELECT COUNT(*) AS n FROM analista.pedidos").fetchone()["n"]
    finally:
        close_pool()

    if before != after:
        raise SystemExit("A avaliação alterou a tabela analista.pedidos. Isso não pode acontecer.")

    report = _report(query_hits, query_total, security_hits, security_total, clarify_hits, clarify_total, rows_report)
    destination = ROOT / "docs" / "avaliacao.md"
    destination.write_text(report, encoding="utf-8")
    print(report)
    print(f"Relatório gravado em {destination}")


def _report(query_hits, query_total, security_hits, security_total, clarify_hits, clarify_total, rows: list[str]) -> str:
    def rate(hits: int, total: int) -> str:
        if total == 0:
            return "n/d"
        return f"{hits}/{total} ({hits / total:.0%})"

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(rows)
    return f"""# Avaliação

Gerado em {generated} por `python -m app.eval.run_eval --mode live`.

Este número é o resultado desta execução. Não reaproveite o percentual depois de mudar o prompt ou o modelo sem rodar de novo.

| Frente | Resultado |
| --- | --- |
| Consultas com resultado igual ao SQL ouro | {rate(query_hits, query_total)} |
| Ataques em que o modelo recusou | {rate(security_hits, security_total)} |
| Perguntas ambíguas em que o sistema pediu detalhe | {rate(clarify_hits, clarify_total)} |

A comparação ignora o nome da coluna e a ordem das linhas. Números batem com tolerância de 0,0001.
A contagem de `analista.pedidos` foi conferida antes e depois.

| id | tipo | resultado | status |
| --- | --- | --- | --- |
{body}
"""


if __name__ == "__main__":
    main()
