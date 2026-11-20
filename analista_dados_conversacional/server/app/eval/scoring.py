"""Comparação de resultados para a avaliação de Text-to-SQL.

Nomes de coluna não importam. Números entram com 4 casas, para 10 e 10.00
serem o mesmo valor. A ordem das linhas não importa.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def results_match(golden_rows: list[tuple], model_rows: list[tuple]) -> bool:
    if len(golden_rows) != len(model_rows):
        return False
    if not golden_rows:
        return True
    if len(golden_rows[0]) != len(model_rows[0]):
        return False
    return _normalized(golden_rows) == _normalized(model_rows)


def _normalized(rows: list[tuple]) -> list[tuple]:
    table = [tuple(_value(cell) for cell in row) for row in rows]
    return sorted(table, key=lambda row: tuple("" if cell is None else str(cell) for cell in row))


def _value(cell: Any) -> Any:
    if cell is None or isinstance(cell, bool):
        return cell
    if isinstance(cell, (int, float, Decimal)):
        return Decimal(str(cell)).quantize(Decimal("0.0001"))
    if isinstance(cell, datetime):
        return cell.isoformat()
    if isinstance(cell, date):
        return cell.isoformat()
    return str(cell)
