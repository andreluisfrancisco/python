from datetime import date
from decimal import Decimal

from app.eval.scoring import results_match


def test_numero_e_ordem_nao_importam():
    golden = [(Decimal("10.00"), date(2025, 1, 1)), (Decimal("2.5"), date(2025, 2, 1))]
    model = [(2.5000, date(2025, 2, 1)), (10, date(2025, 1, 1))]
    assert results_match(golden, model)


def test_coluna_extra_reprova():
    assert results_match([(1,)], [(1, "extra")]) is False
