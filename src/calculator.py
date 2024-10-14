import bisect
from dataclasses import dataclass
from functools import cache, cached_property
from itertools import accumulate, chain, count, repeat, starmap
from operator import mul

import yfinance as yf
from finvizfinance.quote import finvizfinance

DEFAULT_DISCOUNT_RATE = 0.10


ticker_price_dict = {}


def calc_discount_rate(beta: float) -> float:
    beta_values = [0.8, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
    discount_rates = [0.05, 0.06, 0.065, 0.07, 0.075, 0.08, 0.085, 0.09]
    i = min(len(beta_values) - 1, bisect.bisect_left(beta_values, beta))
    return discount_rates[i]


def intrinsic_value(
    free_cash_flow: float,
    total_debt: float,
    total_cash: float,
    shares_outstanding: float,
    growth_rates: list[tuple[float, int]],
    discount_rate: float,
) -> float:
    cash_per_share = total_cash / shares_outstanding
    debt_per_share = total_debt / shares_outstanding

    discount_factors = map(pow, repeat(1 + discount_rate), count(-1, -1))
    growth_rates = [(1 + growth_rate, years) for growth_rate, years in growth_rates]
    projected_cash_flows = accumulate(
        chain.from_iterable(starmap(repeat, growth_rates)), mul
    )
    discounted_values = map(mul, projected_cash_flows, discount_factors)
    present_value = sum(free_cash_flow * x for x in discounted_values)

    return (present_value / shares_outstanding) - debt_per_share + cash_per_share


@dataclass
class Stock:
    ticker: str

    def __post_init__(self) -> None:
        self._yf_data = yf.Ticker(self.ticker)
        self._fv_data = finvizfinance(self.ticker).ticker_fundament(raw=False)

        self.growth_rate = self._fv_data["EPS next 5Y"]

        try:
            self.total_debt = self._yf_data.balance_sheet.loc["Total Debt"].iloc[0]
        except KeyError:
            self.total_debt = 1.0

        try:
            self.total_cash = self._yf_data.balance_sheet.loc[
                "Cash Cash Equivalents And Short Term Investments"
            ].iloc[0]
        except Exception:
            self.total_cash = self._yf_data.balance_sheet.loc[
                "Cash And Cash Equivalents"
            ].iloc[0]
        # self.operating_cash_flow = self._info["operatingCashflow"]
        self.free_cash_flow = self._info.get("freeCashflow", 0)
        self.shares_outstanding = self._info["sharesOutstanding"]
        self.price
        try:
            self.beta = self._info["beta"]
            self.discount_rate = calc_discount_rate(self.beta)
        except Exception:
            self.discount_rate = DEFAULT_DISCOUNT_RATE

    @cached_property
    def _info(self) -> dict:
        return self._yf_data.info

    @property
    def price(self) -> float:
        ticker_price_dict[self.ticker] = self._info["previousClose"]
        return ticker_price_dict[self.ticker]

    def intrinsic_value(
        self,
        growth_rates: list[tuple[float, int]] | None = None,
        discount_rate: float | None = None,
    ) -> float:
        # rate_increase = 1 / (1 - buyback_rate)
        if growth_rates is None:
            growth_rates = [
                (self.growth_rate, 5),
                (self.growth_rate / 2, 5),
                (self.growth_rate / 4, 10),
            ]  # type: ignore
        if discount_rate is None:
            discount_rate = self.discount_rate
        return intrinsic_value(
            self.free_cash_flow,
            self.total_debt,  # type: ignore
            self.total_cash,  # type: ignore
            self.shares_outstanding,
            growth_rates,  # type: ignore
            discount_rate,
        )
