from datetime import datetime
import math
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from itertools import accumulate
from operator import mul
from typing import Any, Literal

import pandas as pd
from pprint import pprint
import yfinance as yf

# from finvizfinance.quote import finvizfinance
from pandas import DataFrame

try:
    from utils import uncompress
except ImportError:
    from src.utils import uncompress


RISK_FREE_RATE = 0.045
EXPECTED_MARKET_RETURN = 0.08
MARKET_RISK_PREMIUM = EXPECTED_MARKET_RETURN - RISK_FREE_RATE
DEFAULT_DISCOUNT_RATE = 0.10
DEFAULT_GROWTH_RATE = 0.10


def cost_of_equity(beta: float) -> float:
    return RISK_FREE_RATE + beta * MARKET_RISK_PREMIUM


def get_default(
    df: pd.DataFrame,
    /,
    key: str,
    fallbacks: list[str] | None = None,
    col: int = 0,
    default: Any = 0.0,
) -> Any:
    if fallbacks is None:
        fallbacks = []

    try:
        return df.loc[key].iloc[col]
    except KeyError:
        for key in fallbacks:
            try:
                return df.loc[key].iloc[col]
            except KeyError:
                pass
    return default


@dataclass
class Stock:
    ticker: str = ""

    def __post_init__(self) -> None:
        if not self.ticker:
            self.buyback_rate = 0.0
            self.total_debt = 0.0
            self.total_cash = 0.0
            self.free_cash_flow = 100.0
            self.shares_outstanding = 100
            self.price = 100.0
            self.beta = 1.0
            self.growth_rate = 0.10
            self.discount_rate = DEFAULT_DISCOUNT_RATE
        else:
            info = self._yf_data.info
            self.buyback_rate = 0.0
            self.growth_rate = 0.0

            if self.growth_rate is None:
                self.growth_rate = DEFAULT_GROWTH_RATE

            self.total_debt = get_default(self.balance_sheet, key="Total Debt")
            self.total_cash = get_default(
                self.balance_sheet,
                key="Cash Cash Equivalents And Short Term Investments",
                fallbacks=["Cash And Cash Equivalents"],
            )
            self.free_cash_flow = info.get(
                "freeCashflow", self._yf_data.quarterly_cash_flow.iloc[0, :4].sum()
            )
            self.shares_outstanding = info.get("sharesOutstanding", 1)
            self.price = info.get("previousClose", 0)
            try:
                self.beta = info["beta"]
                self.discount_rate = round(cost_of_equity(self.beta), 3)
            except Exception:
                self.discount_rate = DEFAULT_DISCOUNT_RATE

        self.growth_rates = [
            (self.growth_rate, 5),
            (self.growth_rate / 2, 5),
            (self.growth_rate / 4, 10),
        ]

    @property
    def free_cash_flow(self) -> float:
        return self._free_cash_flow

    def fcf_history(
        self, period: Literal["annual", "quarterly"] = "quarterly"
    ) -> dict[datetime, float]:
        if period == "quarterly":
            fcf = self._yf_data.quarterly_cash_flow.iloc[0, :]
            return {k.to_pydatetime(): v for k, v in fcf.to_dict().items()}
        else:
            raise ValueError

    @free_cash_flow.setter
    def free_cash_flow(self, value: float) -> None:
        self._free_cash_flow = value

    @property
    def growth_rates(self) -> list[tuple[float, int]]:
        return self._growth_rates

    @growth_rates.setter
    def growth_rates(self, rates: list[tuple[float, int]]) -> None:
        self._growth_rates = [(round(rate, 3), years) for rate, years in rates]

    @cached_property
    def _yf_data(self) -> yf.Ticker:
        return yf.Ticker(self.ticker)

    @property
    def income_stmt(self) -> DataFrame:
        return self._yf_data.income_stmt

    @property
    def balance_sheet(self) -> DataFrame:
        return yf.Ticker(self.ticker).balance_sheet

    @property
    def growth_period(self) -> int:
        return sum(y for _, y in self.growth_rates)

    @property
    def total_assets(self) -> float:
        return self.balance_sheet.loc["Total Assets"].iloc[0]  # type:ignore

    @property
    def current_liabilities(self) -> float:
        return self.balance_sheet.loc["Current Liabilities"].iloc[0]  # type: ignore

    @property
    def discount_factor(self) -> float:
        return 1 / (1 + self.discount_rate)

    @property
    def buyback_growth(self) -> float:
        return 1 / (1 - self.buyback_rate)

    @property
    def cash_per_share(self) -> float:
        return self.total_cash / self.shares_outstanding  # type: ignore

    @property
    def debt_per_share(self) -> float:
        return self.total_debt / self.shares_outstanding  # type: ignore

    @property
    def growth_coeffs(self) -> list[float]:
        values = []
        cumulative_growth = 1
        for growth_rate in uncompress(self.growth_rates):
            cumulative_growth *= (1 + growth_rate) * self.buyback_growth
            values.append(cumulative_growth)
        return values

    @property
    def revenue(self) -> float:
        return self.income_stmt.loc["Total Revenue"].iloc[0]  # type: ignore

    @property
    def gross_profit(self) -> float:
        return self.income_stmt.loc["Gross Profit"].iloc[0]  # type: ignore

    @property
    def gross_margin(self) -> float:
        return self.gross_profit / self.revenue

    @property
    def discount_coeffs(self) -> list[float]:
        return list(accumulate([self.discount_factor] * self.growth_period, mul))

    fcf = free_cash_flow

    @property
    def ebit(self) -> float:
        return self.income_stmt.loc["EBIT"].iloc[0]  # type: ignore

    @property
    def roce(self) -> float:
        return self.ebit / (self.total_assets - self.current_liabilities)

    @property
    def projected_cash_flows(self) -> list[float]:
        cash_flow, values = 0, []
        for growth, discount in zip(self.growth_coeffs, self.discount_coeffs):
            cash_flow += self.free_cash_flow * growth * discount
            values.append(cash_flow)
        return values

    def get_premium(self) -> float:
        value = self.intrinsic_value()
        return math.inf if value == 0 else (self.price / value) - 1

    def intrinsic_value(self) -> float:
        """Calculates the intrinsic value of a stock using a specified method.
        By default, stocks are evaluated using the Discounted Cash Flow (DCF)
        model.
        """
        present_value = self.projected_cash_flows[-1]
        share_value = present_value / self.shares_outstanding
        result = share_value - self.debt_per_share + self.cash_per_share
        return result


if __name__ == "__main__":
    stock = Stock("googl")
