# !usr/bin/env python3

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return """<h1>Hello</h1>"""


def main() -> None:
    app.run(debug=True)


if __name__ == "__main__":
    main()
