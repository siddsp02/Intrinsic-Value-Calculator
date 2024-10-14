# !usr/bin/env python3

from pprint import pprint
import traceback
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from werkzeug import Response
from wtforms import FloatField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

import calculator

app = Flask(__name__)
app.config["SECRET_KEY"] = "a" * 32


class IntrinsicValueCalculator(FlaskForm):
    ticker = StringField("Ticker", validators=[DataRequired(), Length(min=1)])
    free_cash_flow = IntegerField("Free Cash Flow", validators=[DataRequired()])
    growth_rate_y_1_5 = FloatField(
        "Growth Rate Years 1-5",
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_y_6_10 = FloatField(
        "Growth Rate Years 6-10",
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_y_11_20 = FloatField(
        "Growth Rate Years 11-20",
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    discount_rate = FloatField(
        "Discount Rate",
        default=0.12,
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    total_cash = IntegerField(
        "Cash and Short Term Investments", validators=[DataRequired()]
    )
    total_debt = IntegerField("Total Debt", validators=[DataRequired()])
    shares_outstanding = IntegerField("Shares Outstanding", validators=[DataRequired()])
    submit = SubmitField("Calculate Intrinsic Value")


@app.route("/update_fields", methods=["POST"])
def update_fields() -> Response:
    data = request.json
    ticker = data.get("ticker", "")  # type: ignore
    stock = calculator.Stock(ticker)
    return jsonify(
        {
            "growth_rate_y_1_5": round(stock.growth_rate, 3),
            "growth_rate_y_6_10": round(stock.growth_rate / 2, 3),
            "growth_rate_y_11_20": round(stock.growth_rate / 4, 3),
            "free_cash_flow": stock.free_cash_flow,
            "discount_rate": stock.discount_rate,
            "total_cash": stock.total_cash,
            "total_debt": stock.total_debt,
            "shares_outstanding": stock.shares_outstanding,
        }
    )


@app.route("/results", methods=["GET", "POST"])
def results() -> str:

    ticker = request.args.get("ticker", type=str)
    growth_rate_1 = request.args.get("growth_rate_1", type=float)
    growth_rate_2 = request.args.get("growth_rate_2", type=float)
    growth_rate_3 = request.args.get("growth_rate_3", type=float)
    free_cash_flow = request.args.get("free_cash_flow", type=int)
    discount_rate = request.args.get("discount_rate", type=float)
    total_cash = request.args.get("total_cash", type=int)
    total_debt = request.args.get("total_debt", type=int)
    shares_outstanding = request.args.get("shares_outstanding", type=int)

    print(request.args.get("total_debt"), type(request.args.get("total_debt")))

    growth_rates = [(growth_rate_1, 5), (growth_rate_2, 5), (growth_rate_3, 10)]

    result = calculator.intrinsic_value(
        free_cash_flow,  # type: ignore
        total_debt,  # type: ignore
        total_cash,  # type: ignore
        shares_outstanding,  # type: ignore
        growth_rates,  # type: ignore
        discount_rate,  # type: ignore
    )

    return f"""
        <p> Stock Price: ${calculator.ticker_price_dict[ticker]} </p>
        <p> Intrinsic value: ${result:.2f}</p>
    """


@app.route("/", methods=["GET", "POST"])
def main() -> Response | str:
    form = IntrinsicValueCalculator()  # type: IntrinsicValueCalculator
    if form.validate_on_submit():
        return redirect(
            url_for(
                "results",
                ticker=form.ticker.data,
                growth_rate_1=form.growth_rate_y_1_5.data,
                growth_rate_2=form.growth_rate_y_6_10.data,
                growth_rate_3=form.growth_rate_y_11_20.data,
                free_cash_flow=form.free_cash_flow.data,
                discount_rate=form.discount_rate.data,
                total_cash=form.total_cash.data,
                total_debt=form.total_debt.data,
                shares_outstanding=form.shares_outstanding.data,
            )
        )
    return render_template("index.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
