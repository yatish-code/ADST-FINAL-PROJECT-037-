"""Technical indicators (the same ones as your notebook), each one a small function.

Every function takes a pandas Series of closing prices and returns a Series.
"""
import numpy as np


def sma(close, days):
    """Simple moving average: the plain average of the last `days` closing prices."""
    return close.rolling(days).mean()


def ema(close, days):
    """Exponential moving average: like SMA but recent days count more."""
    return close.ewm(span=days, adjust=False).mean()


def rsi(close, days=14):
    """Relative Strength Index, 0-100. Above 70 = rose fast lately, below 30 = fell fast lately."""
    change = close.diff()
    avg_gain = change.clip(lower=0).ewm(alpha=1 / days, adjust=False).mean()
    avg_loss = (-change.clip(upper=0)).ewm(alpha=1 / days, adjust=False).mean()
    value = 100 - 100 / (1 + avg_gain / avg_loss.replace(0, np.nan))
    return value.where(avg_loss != 0, 100)


def macd(close):
    """MACD: gap between a fast and slow average. Returns (line, signal, histogram)."""
    line = ema(close, 12) - ema(close, 26)
    signal = ema(line, 9)
    return line, signal, line - signal


def bollinger(close, days=20):
    """Bollinger bands: a channel 2 standard deviations around the moving average."""
    middle = sma(close, days)
    spread = 2 * close.rolling(days).std()
    return middle - spread, middle, middle + spread


def stochastic(close, k_days=14, d_days=3):
    """Stochastic oscillator, 0-100: where today's close sits in the last 14 days' range.

    Our price file only has closing prices, so we use the highest and lowest *close*.
    """
    lowest, highest = close.rolling(k_days).min(), close.rolling(k_days).max()
    k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    return k, k.rolling(d_days).mean()


def volatility(close):
    """How bumpy the ride is: yearly standard deviation of daily returns, in %."""
    return close.pct_change().std() * np.sqrt(252) * 100


def max_drawdown(close):
    """Biggest fall from a peak to a later low, in % (a negative number)."""
    return (close / close.cummax() - 1).min() * 100


def read_indicators(close):
    """Turn the numbers into a list of {name, value, signal, explain} for beginners."""
    price = close.iloc[-1]
    sma50, sma200 = sma(close, 50).iloc[-1], sma(close, 200).iloc[-1]
    rsi_now = rsi(close).iloc[-1]
    hist = macd(close)[2]
    low, _, high = bollinger(close)
    band_position = (price - low.iloc[-1]) / (high.iloc[-1] - low.iloc[-1])
    stoch_now = stochastic(close)[0].iloc[-1]
    vol = volatility(close.iloc[-252:])

    readings = []

    above = int(price > sma50) + int(price > sma200)
    readings.append(dict(
        name="Trend", value=f"Above {above} of 2 averages",
        signal=["bearish", "neutral", "bullish"][above],
        explain=f"Price is {'above' if price > sma50 else 'below'} its 50-day average "
                f"(${sma50:.2f}) and {'above' if price > sma200 else 'below'} its 200-day average "
                f"(${sma200:.2f}). Being above both usually means an uptrend."))

    signal = "bearish" if rsi_now > 70 else "bullish" if rsi_now < 30 else "neutral"
    meaning = {"bearish": "Overbought: it rose fast, so a pause or dip is more likely.",
               "bullish": "Oversold: it fell fast, so a bounce is more likely.",
               "neutral": "Not stretched in either direction."}[signal]
    readings.append(dict(name="RSI (momentum)", value=f"{rsi_now:.0f} out of 100",
                         signal=signal, explain=meaning))

    rising = hist.iloc[-1] > hist.iloc[-4]
    positive = hist.iloc[-1] > 0
    readings.append(dict(
        name="MACD (momentum shift)", value="Positive" if positive else "Negative",
        signal="bullish" if positive else "bearish",
        explain=f"Short-term momentum is {'above' if positive else 'below'} long-term "
                f"momentum and {'getting stronger' if rising else 'weakening'}."))

    signal = "bearish" if band_position > 0.95 else "bullish" if band_position < 0.05 else "neutral"
    where = ("at the top of" if band_position > 0.95
             else "at the bottom of" if band_position < 0.05 else "inside")
    readings.append(dict(name="Bollinger bands", value=f"{band_position * 100:.0f}% up the channel",
                         signal=signal,
                         explain=f"Price is {where} its usual 20-day channel. "
                                 "Touching an edge often leads to a move back toward the middle."))

    signal = "bearish" if stoch_now > 80 else "bullish" if stoch_now < 20 else "neutral"
    readings.append(dict(name="Stochastic", value=f"{stoch_now:.0f} out of 100", signal=signal,
                         explain="Near 100 means close to its 14-day high, near 0 means close to its low."))

    level = "calm" if vol < 20 else "normal" if vol < 35 else "very bumpy"
    readings.append(dict(name="Volatility", value=f"{vol:.0f}% per year", signal="neutral",
                         explain=f"Price swings over the past year were {level}. "
                                 "Bumpier stocks can gain more but can also fall further."))
    return readings


def overall_mood(readings):
    """Combine the signals into one word: Positive, Mixed or Negative."""
    score = (sum(r["signal"] == "bullish" for r in readings)
             - sum(r["signal"] == "bearish" for r in readings))
    return "Positive" if score >= 2 else "Negative" if score <= -2 else "Mixed"
