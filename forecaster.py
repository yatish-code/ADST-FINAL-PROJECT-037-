"""Price forecasting.

The idea, in four steps:
  1. For every stock and every day, describe the situation with ~15 numbers ("features"):
     recent returns, RSI, MACD, distance from moving averages, and so on.
  2. Look up what the stock actually did over the NEXT 5 / 10 / 21 trading days.
  3. Train ONE model on all 47 stocks together, so it learns from ~35,000 examples
     instead of ~750 for a single stock.
  4. Test it honestly: train on the older 80% of dates, then check it on the newest
     20% that it has never seen. Those test results are shown on the website.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import indicators as ind

HORIZONS = {5: "1 week", 10: "2 weeks", 21: "1 month"}   # trading days ahead
TEST_SHARE = 0.20                                        # newest 20% of dates are the exam


def build_features(prices):
    """Returns {ticker: table of features}. Every feature is a ratio, so stocks are comparable."""
    log_prices = np.log(prices)
    daily = log_prices.diff()
    market = daily.mean(axis=1)
    features = {}

    for ticker in prices.columns:
        close, table = prices[ticker], pd.DataFrame(index=prices.index)

        for days in (1, 5, 10, 21):
            table[f"return_{days}d"] = log_prices[ticker].diff(days)
        table["volatility_21d"] = daily[ticker].rolling(21).std()
        table["gap_sma20"] = close / ind.sma(close, 20) - 1
        table["gap_sma50"] = close / ind.sma(close, 50) - 1
        table["rsi"] = ind.rsi(close)
        table["macd_hist"] = ind.macd(close)[2] / close
        low, _, high = ind.bollinger(close)
        table["bollinger_position"] = (close - low) / (high - low)
        table["stochastic_k"] = ind.stochastic(close)[0]
        table["below_3m_high"] = close / close.rolling(63).max() - 1

        table["market_5d"] = market.rolling(5).sum()
        table["market_21d"] = market.rolling(21).sum()
        table["vs_market_21d"] = table["return_21d"] - table["market_21d"]
        features[ticker] = table
    return features


def new_model():
    """A gradient-boosting model, kept deliberately small so it does not memorise noise."""
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=150,
                                         min_samples_leaf=100, l2_regularization=1.0,
                                         random_state=0)


def confidence_label(ic):
    """Plain-English trust level from the information coefficient (IC) on unseen data."""
    return "Medium" if ic >= 0.08 else "Low" if ic >= 0.02 else "Very low"


class Forecaster:
    def __init__(self, prices):
        self.prices = prices
        self.features = build_features(prices)
        self.columns = list(next(iter(self.features.values())).columns)
        self.results = {}

    def train(self):
        for horizon in HORIZONS:
            self.results[horizon] = self._train_one(horizon)

    def _training_table(self, horizon):
        parts = []
        for ticker, table in self.features.items():
            future = np.log(self.prices[ticker].shift(-horizon) / self.prices[ticker])
            parts.append(table.assign(target=future, ticker=ticker).dropna())
        return pd.concat(parts)

    def _train_one(self, horizon):
        data = self._training_table(horizon)
        dates = data.index.unique().sort_values()
        cut = int(len(dates) * (1 - TEST_SHARE))
        train = data[data.index <= dates[cut - horizon]]
        test = data[data.index >= dates[cut]]

        exam_model = new_model().fit(train[self.columns], train["target"])
        predicted = exam_model.predict(test[self.columns])
        ic = float(np.corrcoef(predicted, test["target"])[0, 1])

        weight = float(np.clip(2 * ic, 0, 1))
        average = float(train["target"].mean())
        blended = weight * predicted + (1 - weight) * average

        holdout = pd.DataFrame({"ticker": test["ticker"], "actual": test["target"],
                                "predicted": blended})
        return dict(
            model=new_model().fit(data[self.columns], data["target"]),
            weight=weight, average=float(data["target"].mean()), ic=ic, holdout=holdout,
            test_start=dates[cut].strftime("%b %Y"), test_end=dates[-1].strftime("%b %Y"))

    @staticmethod
    def _direction_scores(rows):
        rows = rows.dropna(subset=["predicted", "actual"])
        if rows.empty:
            return 0, 0
        model = float((np.sign(rows["predicted"]) == np.sign(rows["actual"])).mean())
        always_up = float((rows["actual"] > 0).mean())
        return round(model * 100), round(always_up * 100)

    def forecast(self, ticker, horizon):
        close = self.prices[ticker]
        last_price, last_date = float(close.iloc[-1]), close.index[-1]
        today = self.features[ticker].iloc[[-1]][self.columns]

        scorecard, points = [], {0: (0.0, 0.0, 0.0)}
        for h, res in self.results.items():
            raw = float(res["model"].predict(today)[0])
            mid = res["weight"] * raw + (1 - res["weight"]) * res["average"]

            rows = res["holdout"][res["holdout"]["ticker"] == ticker]
            errors = rows["actual"] - rows["predicted"]
            low = mid + min(float(errors.quantile(0.10)), 0)
            high = mid + max(float(errors.quantile(0.90)), 0)
            points[h] = (mid, low, high)

            stock_acc, stock_base = self._direction_scores(rows)
            all_acc, all_base = self._direction_scores(res["holdout"])
            scorecard.append(dict(
                horizon=h, label=HORIZONS[h],
                expected_change=round(float((np.exp(mid) - 1) * 100), 2),
                low_price=round(float(last_price * np.exp(low)), 2),
                high_price=round(float(last_price * np.exp(high)), 2),
                stock_accuracy=stock_acc, stock_baseline=stock_base,
                all_accuracy=all_acc, all_baseline=all_base,
                confidence=confidence_label(res["ic"]), test_period=f"{res['test_start']} to {res['test_end']}"))

        xs = sorted(points)
        days = np.arange(0, horizon + 1)
        path = {k: np.interp(days, xs, [points[x][i] for x in xs]) for i, k in enumerate(["mid", "low", "high"])}
        future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=horizon)
        chart = dict(dates=[d.strftime("%Y-%m-%d") for d in future_dates],
                     **{k: [round(last_price * float(np.exp(v)), 2) for v in path[k][1:]] for k in path})

        picked = next(s for s in scorecard if s["horizon"] == horizon)
        return dict(chart=chart, scorecard=scorecard, picked=picked,
                    summary=self._summary(picked, last_price))

    @staticmethod
    def _summary(pick, last_price):
        change = pick["expected_change"]
        half_range = (pick["high_price"] - pick["low_price"]) / 2 / last_price * 100
        strength = abs(change) / half_range if half_range else 0
        lean = "No clear lean" if strength < 0.15 else "Leaning up" if change > 0 else "Leaning down"
        mid_price = last_price * (1 + change / 100)
        text = (f"In about {pick['label']}, the price could be near ${mid_price:,.2f} "
                f"({change:+.1f}%), with a likely range of ${pick['low_price']:,.2f} "
                f"to ${pick['high_price']:,.2f}.")
        caveat = ""
        if pick["confidence"] != "Medium":
            caveat = ("On past prices it had not seen, the model did not find a reliable pattern at this "
                      "horizon, so this estimate is mostly the stock's long-run average drift. "
                      "Treat the range as more useful than the middle number.")
        return dict(lean=lean, text=text, caveat=caveat)
