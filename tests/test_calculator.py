import math

from src.calculator import Stock


def test_intrinsic_value() -> None:
    stock = Stock(ticker="")  # For now we don't want to access actual data.

    # Test against some fixed/known values.
    stock.free_cash_flow = 49_518
    stock.total_debt = 18_387
    stock.total_cash = 58_120
    stock.shares_outstanding = 2_600
    stock.discount_rate = 0.066
    stock.growth_rate = 0.15
    stock.growth_rates = [(0.15, 5), (0.075, 5), (0.04, 10)]

    assert math.isclose(
        stock.intrinsic_value(),
        532.25,
        abs_tol=0.01,
    )
