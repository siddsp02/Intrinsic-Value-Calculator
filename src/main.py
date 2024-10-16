# !usr/bin/env python3

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from werkzeug import Response
from wtforms import FloatField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length

import calculator
from utils import parse_dict

app = Flask(__name__)
app.config["SECRET_KEY"] = "a" * 32


class IntrinsicValueCalculator(FlaskForm):
    ticker = StringField("Ticker", validators=[DataRequired(), Length(min=1)])
    free_cash_flow = IntegerField("Free Cash Flow", validators=[InputRequired()])
    growth_rate_y_1_5 = FloatField(
        "Growth Rate Years 1-5",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_y_6_10 = FloatField(
        "Growth Rate Years 6-10",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    growth_rate_y_11_20 = FloatField(
        "Growth Rate Years 11-20",
        validators=[InputRequired()],
        render_kw={"type": "number", "min": "-1", "step": "0.001"},
    )
    discount_rate = FloatField(
        "Discount Rate",
        default=0.12,
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
            "buyback_rate": stock.buyback_rate,
            "shares_outstanding": stock.shares_outstanding,
        }
    )


@app.route("/results", methods=["GET", "POST"])
def results() -> str:
    data = parse_dict(request.args)
    stock = calculator.Stock(data["ticker"])  # type: ignore
    stock.growth_rate = data["growth_rate_1"]  # type: ignore
    stock.growth_rates = [
        (round(data["growth_rate_1"], 3), 5),  # type: ignore
        (round(data["growth_rate_2"], 3), 5),  # type: ignore
        (round(data["growth_rate_3"], 3), 10),  # type: ignore
    ]
    result = stock.intrinsic_value()

    return f"""
        <p> Stock Price: ${stock.price} </p>
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
                buyback_rate=form.buyback_rate.data,
            )
        )
    return render_template("index.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
