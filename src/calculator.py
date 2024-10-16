from dataclasses import dataclass
from functools import cache
from typing import cast

import yfinance as yf
from finvizfinance.quote import finvizfinance

try:
    from utils import uncompress
except ImportError:
    from src.utils import uncompress

RISK_FREE_RATE = 0.041
EXPECTED_MARKET_RETURN = 0.08
MARKET_RISK_PREMIUM = EXPECTED_MARKET_RETURN - RISK_FREE_RATE
DEFAULT_DISCOUNT_RATE = 0.10


def cost_of_equity(beta: float) -> float:
    return RISK_FREE_RATE + beta * MARKET_RISK_PREMIUM


@dataclass
class Stock:
    ticker: str = ""

    def __post_init__(self) -> None:
        if not self.ticker:
            self.buyback_rate = 0.0
            self.total_debt = 0.0
            self.total_cash = 0.0
            self.free_cash_flow = 100.0
            self.shares_oustanding = 100
            self.price = 100.0
            self.beta = 1.0
            self.growth_rate = 0.10
            self.discount_rate = DEFAULT_DISCOUNT_RATE
        else:
            yf_data = yf.Ticker(self.ticker)
            fv_data = finvizfinance(self.ticker).ticker_fundament(raw=False)
            balance_sheet = yf_data.balance_sheet
            info = yf_data.info
            self.buyback_rate = 0.0
            self.growth_rate = cast(float, fv_data["EPS next 5Y"])

            try:
                self.total_debt = balance_sheet.loc["Total Debt"].iloc[0]
            except KeyError:
                self.total_debt = 0.0

            try:
                self.total_cash = balance_sheet.loc[
                    "Cash Cash Equivalents And Short Term Investments"
                ].iloc[0]
            except Exception:
                self.total_cash = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]

            self.free_cash_flow = info.get(
                "freeCashflow", yf_data.quarterly_cash_flow.iloc[0, :4].sum()
            )
            self.shares_outstanding = info["sharesOutstanding"]
            self.price = info["previousClose"]
            try:
                self.beta = info["beta"]
                self.discount_rate = round(cost_of_equity(self.beta), 3)
            except Exception:
                self.discount_rate = DEFAULT_DISCOUNT_RATE

        self.growth_rates = [
            (round(self.growth_rate, 3), 5),
            (round(self.growth_rate / 2, 3), 5),
            (round(self.growth_rate / 4, 3), 10),
        ]

    @property
    def discount_factor(self) -> float:
        return 1 / (1 + self.discount_rate)

    @property
    def buyback_growth(self) -> float:
        return 1 / (1 - self.buyback_rate)

    @property
    def cash_per_share(self) -> float:
        return self.total_cash / self.shares_outstanding

    @property
    def debt_per_share(self) -> float:
        return self.total_debt / self.shares_outstanding

    @property
    def projected_cash_flows(self) -> list[float]:
        discount, growth, cash_flow, values = 1, 1, 0, []
        for growth_rate in uncompress(self.growth_rates):
            growth_rate = (1 + growth_rate) * self.buyback_growth
            growth *= growth_rate
            discount *= self.discount_factor
            cash_flow += self.free_cash_flow * growth * discount
            values.append(cash_flow)
        return values

    def intrinsic_value(self) -> float:
        present_value = self.projected_cash_flows[-1]
        share_value = present_value / self.shares_outstanding
        return share_value - self.debt_per_share + self.cash_per_share


if __name__ == "__main__":
    googl = Stock("GOOGL")
    v = googl.intrinsic_value()
    print(v)
