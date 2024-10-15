import math

from src.calculator import intrinsic_value


def test_intrinsic_value() -> None:
    assert math.isclose(
        intrinsic_value(
            free_cash_flow=49_518,
            total_debt=18_387,
            total_cash=58_120,
            shares_outstanding=2_600,
            discount_rate=0.066,
            growth_rates=[(0.15, 5), (0.075, 5), (0.04, 10)],
        ),
        532.25,
        abs_tol=0.01,
    )
