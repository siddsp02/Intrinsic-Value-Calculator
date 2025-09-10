# !usr/bin/env python3


import plotly.express as px
import plotly.io as pio
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from werkzeug import Response
from wtforms import FloatField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length

try:
    from calculator import DEFAULT_DISCOUNT_RATE, Stock
    from utils import parse_dict
except ImportError:
    from src.calculator import DEFAULT_DISCOUNT_RATE, Stock
    from src.utils import parse_dict

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"


class IntrinsicValueCalculator(FlaskForm):
    ticker = StringField("Ticker", validators=[DataRequired(), Length(min=1)])
    free_cash_flow = IntegerField("Free Cash Flow", validators=[InputRequired()])
    growth_rate_1 = FloatField(
        "Growth Rate Years 1-5",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_2 = FloatField(
        "Growth Rate Years 6-10",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_3 = FloatField(
        "Growth Rate Years 11-20",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    discount_rate = FloatField(
        "Discount Rate",
        default=DEFAULT_DISCOUNT_RATE,
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    total_cash = IntegerField(
        "Cash and Short Term Investments", validators=[InputRequired()]
    )
    total_debt = IntegerField("Total Debt", validators=[InputRequired()])
    buyback_rate = FloatField(
        "Buyback Rate",
        default=0.0,
        validators=[InputRequired()],
        render_kw={"type": "number", "step": "0.001"},
    )
    shares_outstanding = IntegerField("Shares Outstanding", validators=[DataRequired()])
    submit = SubmitField("Calculate Intrinsic Value")


@app.route("/update_fields", methods=["POST"])
def update_fields() -> Response:
    data = request.json
    ticker = data.get("ticker", "")  # type: ignore
    stock = Stock(ticker)
    return jsonify(
        {
            "growth_rate_1": round(stock.growth_rate, 3),
            "growth_rate_2": round(stock.growth_rate / 2, 3),
            "growth_rate_3": round(stock.growth_rate / 4, 3),
            "free_cash_flow": stock.free_cash_flow,
            "discount_rate": stock.discount_rate,
            "total_cash": stock.total_cash,
            "total_debt": stock.total_debt,
            "buyback_rate": stock.buyback_rate,
            "shares_outstanding": stock.shares_outstanding,
        }
    )


def update_stock_values_from_data(data: dict, stock: Stock) -> None:
    stock.total_cash = data["total_cash"]
    stock.total_debt = data["total_debt"]
    stock.growth_rate = data["growth_rate_1"]
    stock.free_cash_flow = data["free_cash_flow"]
    stock.discount_rate = data["discount_rate"]
    stock.shares_outstanding = data["shares_outstanding"]
    stock.buyback_rate = data["buyback_rate"]
    stock.growth_rates = [
        (data["growth_rate_1"], 5),
        (data["growth_rate_2"], 5),
        (data["growth_rate_3"], 10),
    ]


@app.route("/intrinsic-value-calculator", methods=["GET", "POST"])
def results() -> str:
    data = parse_dict(request.args)
    stock = Stock(data["ticker"])  # type: ignore

    update_stock_values_from_data(data, stock)

    fig_1 = px.bar(x=list(range(1, 21)), y=stock.projected_cash_flows)
    fig_1.update_layout(
        width=700, height=500, template="seaborn", title="Projected Cash Flows"
    )

    # fcf_hist = stock.fcf_history()

    # fig_2 = px.bar(x=fcf_hist.keys(), y=fcf_hist.values())
    # fig_2.update_layout(
    #     width=700, height=500, template="seaborn", title="Free Cash Flow History"
    # )

    plot_config = {
        "full_html": False,
        "config": {"displayModeBar": False},
    }

    return render_template(
        "results.html",
        stock=stock,
        round=round,
        plot_1=pio.to_html(fig_1, **plot_config),
        # plot_2=pio.to_html(fig_2, **plot_config),
    )


@app.route("/", methods=["GET", "POST"])
def main() -> Response | str:
    form = IntrinsicValueCalculator()  # type: IntrinsicValueCalculator
    if form.validate_on_submit():
        return redirect(
            url_for(
                "results",
                ticker=form.ticker.data,
                growth_rate_1=form.growth_rate_1.data,
                growth_rate_2=form.growth_rate_2.data,
                growth_rate_3=form.growth_rate_3.data,
                free_cash_flow=form.free_cash_flow.data,
                discount_rate=form.discount_rate.data,
                total_cash=form.total_cash.data,
                total_debt=form.total_debt.data,
                shares_outstanding=form.shares_outstanding.data,
                buyback_rate=form.buyback_rate.data,
            )
        )
    return render_template("index.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
