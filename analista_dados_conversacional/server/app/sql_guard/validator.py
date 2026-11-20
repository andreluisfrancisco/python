"""Validador de SQL gerado pelo modelo.

A consulta do usuário nunca é concatenada no SQL. O modelo escreve a
consulta, e só um SELECT de tabela permitida segue para o banco. O executor
ainda abre a transação como somente leitura, no papel analista_leitura.
"""

from __future__ import annotations

import re

import sqlparse

ALLOWED_TABLES = frozenset(
    {
        "regioes",
        "lojas",
        "vendedores",
        "categorias",
        "produtos",
        "clientes",
        "pedidos",
        "itens_pedido",
    }
)
ALLOWED_SCHEMA = "analista"

ALLOWED_FUNCTIONS = frozenset(
    {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "string_agg",
        "array_agg",
        "bool_and",
        "bool_or",
        "row_number",
        "rank",
        "dense_rank",
        "ntile",
        "lag",
        "lead",
        "first_value",
        "last_value",
        "percentile_cont",
        "percentile_disc",
        "coalesce",
        "nullif",
        "greatest",
        "least",
        "abs",
        "ceil",
        "ceiling",
        "floor",
        "trunc",
        "round",
        "mod",
        "div",
        "date_trunc",
        "date_part",
        "extract",
        "to_char",
        "to_date",
        "to_timestamp",
        "make_date",
        "age",
        "lower",
        "upper",
        "initcap",
        "length",
        "char_length",
        "trim",
        "btrim",
        "ltrim",
        "rtrim",
        "left",
        "right",
        "replace",
        "concat",
        "concat_ws",
        "substring",
        "substr",
        "position",
        "strpos",
        "split_part",
        "cast",
        "overlay",
        "width_bucket",
        "over",
    }
)

ALLOWED_TYPE_NAMES = frozenset(
    {
        "int",
        "int2",
        "int4",
        "int8",
        "integer",
        "bigint",
        "smallint",
        "numeric",
        "decimal",
        "real",
        "float",
        "float4",
        "float8",
        "text",
        "varchar",
        "char",
        "bpchar",
        "boolean",
        "bool",
        "date",
        "timestamp",
        "timestamptz",
        "interval",
        "time",
    }
)

# Funções cuja sintaxe usa FROM/IN dentro dos parênteses.
_FUNCTIONS_WITH_INNER_FROM = ("extract", "trim", "btrim", "ltrim", "rtrim", "substring", "overlay", "position")

_FORBIDDEN = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|"
    r"execute|call|do|set|reset|vacuum|analyze|comment|listen|notify|load|"
    r"discard|lock|reindex|cluster|refresh|merge|into|returning|fetch|"
    r"outfile|pg_sleep|pg_read_file|pg_ls_dir|pg_read_binary_file|"
    r"lo_import|lo_export|lo_from_bytea|dblink|pg_terminate_backend|"
    r"pg_cancel_backend|query_to_xml|pg_catalog|information_schema"
    r")\b",
    re.IGNORECASE,
)

_FUNCTION_CALL = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
# Palavras que aparecem com parênteses e não são funções chamáveis pelo modelo.
_NOT_FUNCTIONS = frozenset(
    {
        "in",
        "exists",
        "filter",
        "and",
        "or",
        "not",
        "like",
        "ilike",
        "between",
        "is",
        "on",
        "when",
        "then",
        "else",
        "end",
        "select",
        "from",
        "where",
        "group",
        "order",
        "having",
        "limit",
        "offset",
        "union",
        "except",
        "intersect",
        "all",
        "any",
        "some",
        "case",
        "as",
        "with",
        "values",
        "row",
        "rows",
        "using",
    }
)
_TABLE_REF = re.compile(
    r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)",
    re.IGNORECASE,
)
_CTE_NAME = re.compile(
    r"(?:with(?:\s+recursive)?|,)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\([^)]*\))?\s*as\s*\(",
    re.IGNORECASE,
)
_LIMIT_NUMBER = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)
_STRING = re.compile(r"'(?:''|[^'])*'")


class SqlRejected(ValueError):
    """A consulta não passou no validador e não deve chegar ao banco."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate(sql: str, *, max_rows: int = 200) -> str:
    """Devolve o SQL limpo, com LIMIT máximo, ou recusa com um motivo curto."""
    if not sql or not sql.strip():
        raise SqlRejected("A consulta veio vazia.")
    if len(sql) > 4000:
        raise SqlRejected("A consulta passou de 4000 caracteres.")
    if "$$" in sql or '"' in sql:
        raise SqlRejected("Identificadores entre aspas e dollar-quoting não são aceitos.")

    cleaned = sqlparse.format(sql, strip_comments=True).strip().rstrip(";").strip()
    statements = [part for part in sqlparse.parse(cleaned) if str(part).strip()]
    if len(statements) != 1:
        raise SqlRejected("Só uma consulta SELECT é aceita. Vários comandos foram recusados.")

    statement = statements[0]
    first = statement.token_first(skip_cm=True)
    first_word = first.value.lower() if first is not None else ""
    if statement.get_type() != "SELECT" and first_word != "with":
        raise SqlRejected("Só SELECT (ou WITH ... SELECT) é aceito.")

    masked = _STRING.sub("''", cleaned)
    forbidden = _FORBIDDEN.search(masked)
    if forbidden:
        raise SqlRejected(f"Comando ou função não permitido: {forbidden.group(1).lower()}.")
    if re.search(r"\bfor\s+(update|share|no\s+key\s+update|key\s+share)\b", masked, re.IGNORECASE):
        raise SqlRejected("SELECT FOR UPDATE/SHARE não é aceito.")

    _reject_unknown_functions(masked)
    tables = _tables(masked)
    if not tables:
        raise SqlRejected("A consulta precisa ler ao menos uma tabela do schema analista.")

    allowed_names = set(ALLOWED_TABLES)
    allowed_names.update(name.lower() for name in _CTE_NAME.findall(masked))
    for qualifier, name in tables:
        if qualifier not in {None, ALLOWED_SCHEMA}:
            raise SqlRejected(f"Schema não permitido: {qualifier}.")
        if name not in allowed_names:
            raise SqlRejected(f"Tabela não permitida: {name}.")
        if qualifier is None and name not in allowed_names:
            raise SqlRejected(f"Tabela não permitida: {name}.")

    if not any(name in ALLOWED_TABLES for _, name in tables):
        raise SqlRejected("A consulta precisa usar uma tabela do schema analista.")

    return _enforce_limit(cleaned, max_rows)


def _reject_unknown_functions(masked_sql: str) -> None:
    for name in _FUNCTION_CALL.findall(masked_sql):
        lowered = name.lower()
        if lowered in _NOT_FUNCTIONS:
            continue
        if lowered.startswith("pg_") or lowered.startswith("lo_") or lowered.startswith("dblink"):
            raise SqlRejected(f"Função não permitida: {lowered}.")
        if lowered in ALLOWED_FUNCTIONS or lowered in ALLOWED_TYPE_NAMES:
            continue
        raise SqlRejected(f"Função não permitida: {lowered}.")


def _tables(masked_sql: str) -> set[tuple[str | None, str]]:
    scanned = masked_sql
    for function_name in _FUNCTIONS_WITH_INNER_FROM:
        scanned = _blank_function(scanned, function_name)
    found: set[tuple[str | None, str]] = set()
    for raw in _TABLE_REF.findall(scanned):
        parts = raw.lower().split(".")
        if len(parts) == 1:
            found.add((None, parts[0]))
        else:
            found.add((parts[0], parts[1]))
    return found


def _blank_function(sql: str, name: str) -> str:
    pattern = re.compile(rf"\b{name}\s*\(", re.IGNORECASE)
    pieces: list[str] = []
    cursor = 0
    while True:
        match = pattern.search(sql, cursor)
        if match is None:
            pieces.append(sql[cursor:])
            break
        pieces.append(sql[cursor : match.start()])
        depth = 0
        index = match.end() - 1
        while index < len(sql):
            char = sql[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            index += 1
        pieces.append(f"{name}()")
        cursor = index
    return "".join(pieces)


def _enforce_limit(sql: str, max_rows: int) -> str:
    if max_rows < 1:
        raise SqlRejected("O limite de linhas precisa ser positivo.")
    limit_at = _top_level_limit_span(sql)
    if limit_at is None:
        return f"{sql} LIMIT {max_rows}"
    start, end, value = limit_at
    if value is None:
        raise SqlRejected("Use LIMIT com um número inteiro.")
    if value > max_rows:
        return f"{sql[:start]}LIMIT {max_rows}{sql[end:]}"
    return sql


def _top_level_limit_span(sql: str) -> tuple[int, int, int | None] | None:
    depth = 0
    in_string = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if in_string:
            if char == "'" and index + 1 < len(sql) and sql[index + 1] == "'":
                index += 2
                continue
            if char == "'":
                in_string = False
            index += 1
            continue
        if char == "'":
            in_string = True
            index += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and sql[index : index + 5].lower() == "limit" and _is_boundary(sql, index, index + 5):
            match = _LIMIT_NUMBER.match(sql, index)
            if match is None:
                return (index, index + 5, None)
            return (match.start(), match.end(), int(match.group(1)))
        index += 1
    return None


def _is_boundary(sql: str, start: int, end: int) -> bool:
    before = sql[start - 1] if start else " "
    after = sql[end] if end < len(sql) else " "
    return not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_")
