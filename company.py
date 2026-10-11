"""Company health: yearly financials, key ratios and simple plain-English checks."""
import numpy as np
import pandas as pd


def _clean(value):
    """Turn a missing value (NaN) into None, which becomes `null` in JSON."""
    return None if pd.isna(value) else round(float(value), 2)


def _show(value, template):
    """Format a number for display, or 'n/a' when we have no data."""
    return "n/a" if value is None else template.format(value)


def _rate(value, good, ok, labels, higher_is_better=True):
    """Compare a number with two thresholds and return (label, signal).

    labels = [best, middle, worst]. For things like P/E, where LOWER is better,
    pass higher_is_better=False.
    """
    if value is None:
        return "No data", "neutral"
    if not higher_is_better:                       # flip the scale so "bigger = better" again
        value, good, ok = -value, -good, -ok
    if value >= good:
        return labels[0], "bullish"
    if value >= ok:
        return labels[1], "neutral"
    return labels[2], "bearish"


def get_company(ticker, tables):
    """Everything the 'Company health' tab needs for one stock."""
    if ticker not in tables["revenue"].index:
        return dict(available=False)               # e.g. UNH is missing from the files

    billions = lambda name: [round(float(v) / 1e9, 2) for v in tables[name].loc[ticker]]
    revenue = billions("revenue")

    ratios = tables["stats"].loc[ticker] if ticker in tables["stats"].index else pd.Series(dtype=float)
    valuation = tables["valuation"].loc[ticker] if ticker in tables["valuation"].index else pd.Series(dtype=float)
    margin = _clean(ratios.get("Profit Margin", np.nan))
    roe = _clean(ratios.get("Return on Equity", np.nan))
    pe = _clean(valuation.get("Trailing P/E", np.nan))

    # Average yearly sales growth between the first and last year we have
    first, last, gaps = revenue[0], revenue[-1], len(revenue) - 1
    growth = ((last / first) ** (1 / gaps) - 1) * 100 if first > 0 else None

    # Each check is (name, number, how to display it, (label, signal), one-line explanation)
    checks = [
        ("Sales growth", growth, _show(growth, "{:.1f}% a year"),
         _rate(growth, 10, 3, ["Growing fast", "Growing steadily", "Barely growing"]),
         "How quickly yearly sales have grown since 2019."),
        ("Profit margin", margin, _show(margin, "{:.1f}%"),
         _rate(margin, 15, 5, ["Very profitable", "Profitable", "Thin profits"]),
         "Of every $100 in sales, how many dollars are kept as profit."),
        ("Return on equity", roe, _show(roe, "{:.1f}%"),
         _rate(roe, 15, 8, ["Efficient", "Average", "Weak"]),
         "How much profit the company makes from its owners' money."),
        ("Price vs profit (P/E)", pe, _show(pe, "{:.1f}"),
         _rate(pe, 15, 30, ["Priced low", "Fairly priced", "Priced high"], higher_is_better=False),
         "Dollars investors pay for $1 of yearly profit. A low price is not always a bargain."),
    ]

    return dict(
        available=True,
        years=[int(y) for y in tables["revenue"].columns],
        revenue=revenue, profit=billions("profit"), assets=billions("assets"),
        cash=billions("cash"), equity=billions("equity"),
        checks=[dict(name=n, value=shown, label=r[0], signal=r[1], explain=text)
                for n, _, shown, r, text in checks],
        valuation={k: _clean(valuation.get(k, np.nan))
                   for k in ["Trailing P/E", "Forward P/E", "Price/Sales", "Price/Book", "PEG"]})
