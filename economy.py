"""Economy basics: yearly averages of economic indicators for three stock indexes.

Note: the values in this dataset look simulated (no trend over time, no day-to-day
link between prices), so the website presents it as a learning tool only.
"""
from . import datasets

INDICATORS = {
    "GDP Growth (%)": "How fast the whole economy is growing. Growing economies tend to help company profits.",
    "Inflation Rate (%)": "How fast prices rise. High inflation squeezes shoppers and often leads to higher interest rates.",
    "Unemployment Rate (%)": "Share of people without a job who want one. High unemployment usually means weak spending.",
    "Interest Rate (%)": "The cost of borrowing. Higher rates make loans pricier and often pull stock prices down.",
    "Consumer Confidence Index": "How optimistic households feel. Confident people spend more.",
    "Crude Oil Price (USD per Barrel)": "Oil affects fuel and shipping costs for almost every business.",
    "Gold Price (USD per Ounce)": "Investors often buy gold when they are nervous about the economy.",
}


class Economy:
    def __init__(self):
        data = datasets.load_economy()
        data["Year"] = data["Date"].dt.year
        self.data = data
        self.indexes = sorted(data["Stock Index"].unique())

    def yearly(self, indicator, index):
        """Yearly average of one indicator for one index."""
        if indicator not in INDICATORS or index not in self.indexes:
            raise ValueError("Unknown indicator or index.")
        rows = self.data[self.data["Stock Index"] == index]
        by_year = rows.groupby("Year")[indicator].mean().round(2)
        prices = rows.groupby("Year")["Close Price"].mean().round(0)
        return dict(indicator=indicator, index=index, explain=INDICATORS[indicator],
                    years=[int(y) for y in by_year.index], values=by_year.tolist(),
                    prices=prices.tolist(), rows=len(rows),
                    first_date=rows["Date"].min().strftime("%b %Y"), last_date=rows["Date"].max().strftime("%b %Y"))
