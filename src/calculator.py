from dataclasses import dataclass
from functools import cached_property
from itertools import accumulate, repeat
from operator import mul
from typing import cast

import yfinance as yf
from finvizfinance.quote import finvizfinance

from utils import uncompress

RISK_FREE_RATE = 0.041
EXPECTED_MARKET_RETURN = 0.08
MARKET_RISK_PREMIUM = EXPECTED_MARKET_RETURN - RISK_FREE_RATE
DEFAULT_DISCOUNT_RATE = 0.10


ticker_price_dict = {}


def cost_of_equity(beta: float) -> float:
    return RISK_FREE_RATE + beta * MARKET_RISK_PREMIUM


def intrinsic_value(
    free_cash_flow: float,
    total_debt: float,
    total_cash: float,
    shares_outstanding: float,
    growth_rates: list[tuple[float, int]],
    discount_rate: float,
    buyback_rate: float = 0,
) -> float:
    buyback_growth = 1 / (1 - buyback_rate)

    cash_per_share = total_cash / shares_outstanding
    debt_per_share = total_debt / shares_outstanding

    discount_factors = accumulate(repeat(1 / (1 + discount_rate)), mul)
    growth_rates = [
        ((1 + growth_rate) * buyback_growth, years)
        for growth_rate, years in growth_rates
    ]
    projected_cash_flows = accumulate(uncompress(growth_rates), mul)

    discounted_values = map(mul, projected_cash_flows, discount_factors)
    present_value = sum(free_cash_flow * x for x in discounted_values)

    return (present_value / shares_outstanding) - debt_per_share + cash_per_share


@dataclass
class Stock:
    ticker: str

    def __post_init__(self) -> None:
        self._yf_data = yf.Ticker(self.ticker)
        self._fv_data = finvizfinance(self.ticker).ticker_fundament(raw=False)

        self.buyback_rate = 0.0
        self.growth_rate = cast(float, self._fv_data["EPS next 5Y"])

        try:
            self.total_debt = self._yf_data.balance_sheet.loc["Total Debt"].iloc[0]
        except KeyError:
            self.total_debt = 0.0

        try:
            self.total_cash = self._yf_data.balance_sheet.loc[
                "Cash Cash Equivalents And Short Term Investments"
            ].iloc[0]
        except Exception:
            self.total_cash = self._yf_data.balance_sheet.loc[
                "Cash And Cash Equivalents"
            ].iloc[0]

        self.free_cash_flow: float = self._info.get(
            "freeCashflow", self._yf_data.quarterly_cash_flow.iloc[0, :4].sum()
        )

        self.shares_outstanding = self._info["sharesOutstanding"]
        self.price
        self.growth_rates = [
            (self.growth_rate, 5),
            (self.growth_rate / 2, 5),
            (self.growth_rate / 4, 10),
        ]
        try:
            self.beta = self._info["beta"]
            self.discount_rate = round(cost_of_equity(self.beta), 3)
        except Exception:
            self.discount_rate = DEFAULT_DISCOUNT_RATE

    @cached_property
    def _info(self) -> dict:
        return self._yf_data.info

    @property
    def price(self) -> float:
        ticker_price_dict[self.ticker] = self._info["previousClose"]
        return ticker_price_dict[self.ticker]

    def intrinsic_value(self) -> float:
        return intrinsic_value(
            self.free_cash_flow,
            self.total_debt,  # type: ignore
            self.total_cash,  # type: ignore
            self.shares_outstanding,
            self.growth_rates,
            self.discount_rate,
            self.buyback_rate,
        )
