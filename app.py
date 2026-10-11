from flask import Flask, jsonify, request, send_from_directory

from backend import datasets, indicators
from backend.company import get_company
from backend.economy import Economy, INDICATORS
from backend.forecaster import Forecaster, HORIZONS
from backend.sentiment import NewsMood

app = Flask(__name__, static_folder="static")
app.json.sort_keys = False

INDIA_TICKERS = set(datasets.FULL_INDIAN_TICKERS)

print("Loading data and training models (about 10 seconds)...")
prices = datasets.load_prices()
financials = datasets.load_financials()
forecaster = Forecaster(prices)
forecaster.train()
news_mood = NewsMood()
economy = Economy()
print("Ready. Open http://127.0.0.1:5000")


def error(message, status=400):
    return jsonify(error=message), status


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/stocks")
def stock_list():
    stocks = []
    for ticker in prices.columns:
        market = "India" if ticker in INDIA_TICKERS else "US"
        stocks.append(dict(ticker=ticker, name=datasets.COMPANY_NAMES.get(ticker, ticker), market=market))
    return jsonify(stocks=stocks,
                   horizons=[dict(days=d, label=label) for d, label in HORIZONS.items()],
                   data_ends=prices.index[-1].strftime("%d %b %Y"),
                   data_starts=prices.index[0].strftime("%b %Y"))


@app.get("/api/stock/<ticker>")
def stock(ticker):
    ticker = ticker.upper()
    if ticker not in prices.columns:
        return error(f"We don't have data for '{ticker}'. Pick a stock from the list.", 404)
    horizon = request.args.get("horizon", 21, type=int)
    if horizon not in HORIZONS:
        return error(f"Horizon must be one of {list(HORIZONS)} trading days.")

    close = prices[ticker]
    recent = close.iloc[-252:]
    readings = indicators.read_indicators(close)
    market = "India" if ticker in INDIA_TICKERS else "US"
    return jsonify(
        ticker=ticker, name=datasets.COMPANY_NAMES.get(ticker, ticker), market=market,
        last_date=close.index[-1].strftime("%d %b %Y"), last_price=round(float(close.iloc[-1]), 2),
        changes=dict(day=round(float(close.pct_change().iloc[-1] * 100), 2),
                     month=round(float((close.iloc[-1] / close.iloc[-22] - 1) * 100), 1),
                     year=round(float((close.iloc[-1] / close.iloc[-252] - 1) * 100), 1)),
        history=dict(dates=[d.strftime("%Y-%m-%d") for d in recent.index],
                     close=[round(float(v), 2) for v in recent],
                     sma50=[None if v != v else round(float(v), 2) for v in indicators.sma(close, 50).iloc[-252:]],
                     sma200=[None if v != v else round(float(v), 2) for v in indicators.sma(close, 200).iloc[-252:]]),
        forecast=forecaster.forecast(ticker, horizon),
        indicators=readings, mood=indicators.overall_mood(readings),
        risk=dict(volatility=round(float(indicators.volatility(close.iloc[-252:])), 1),
                  worst_fall=round(float(indicators.max_drawdown(close)), 1),
                  best_day=round(float(close.pct_change().max() * 100), 1),
                  worst_day=round(float(close.pct_change().min() * 100), 1)))


@app.get("/api/company/<ticker>")
def company(ticker):
    ticker = ticker.upper()
    if ticker not in prices.columns:
        return error(f"We don't have data for '{ticker}'.", 404)
    return jsonify(get_company(ticker, financials))


@app.post("/api/sentiment")
def sentiment():
    headlines = [h.strip() for h in (request.get_json(silent=True) or {}).get("headlines", []) if h.strip()]
    if not headlines:
        return error("Paste at least one headline.")
    return jsonify(news_mood.score(headlines[:20]))


@app.get("/api/sentiment/info")
def sentiment_info():
    return jsonify(accuracy=news_mood.accuracy, sentences=news_mood.sentences, examples=news_mood.examples)


@app.get("/api/economy")
def economy_data():
    try:
        return jsonify(economy.yearly(request.args.get("indicator", "Inflation Rate (%)"),
                                      request.args.get("index", "S&P 500")))
    except ValueError as problem:
        return error(str(problem))


@app.get("/api/economy/options")
def economy_options():
    return jsonify(indicators=list(INDICATORS), indexes=economy.indexes)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
