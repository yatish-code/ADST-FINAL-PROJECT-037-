"""Loads the CSV files in the data/ folder. Every other file asks this one for data."""
from pathlib import Path
import pandas as pd
import yfinance as yf

SOURCE_DATA_DIR = Path(r"C:\Users\Bhavesh Yadav\Downloads\stockwise\stockwise\data")
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolve_data_dir():
    """Prefer the package's own data folder; if it's empty, use the original source project data."""
    candidates = [LOCAL_DATA_DIR, SOURCE_DATA_DIR]
    for candidate in candidates:
        if candidate.exists() and any(candidate.iterdir()):
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return LOCAL_DATA_DIR


DATA_DIR = _resolve_data_dir()
INDIA_ARCHIVE_PATH = Path(r"C:\Users\Bhavesh Yadav\Downloads\archive (3).zip")

ACTIVE_INDIAN_TICKERS = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "HINDUNILVR", "ITC",
    "BAJFINANCE", "ASIANPAINT", "HCLTECH", "SUNPHARMA", "MARUTI", "KOTAKBANK", "TITAN",
    "NTPC", "POWERGRID", "AXISBANK", "BHARTIARTL", "INDUSINDBK", "WIPRO", "ULTRACEMCO",
    "TECHM", "CIPLA", "NESTLEIND", "TATASTEEL", "DRREDDY", "M&M", "ONGC", "JSWSTEEL",
    "IOC", "COALINDIA", "GRASIM", "GAIL", "BRITANNIA", "HINDALCO", "EICHERMOT",
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "BAJAJ-AUTO", "BANKBARODA", "HDFCLIFE",
    "ICICIPRULI", "TRENT", "TATACONSUM", "TATAPOWER", "UPL", "YESBANK", "GODREJPROP",
    "ICICIGI", "METROPOLIS", "PAGEIND", "PIDILITIND", "PERSISTENT", "SHRIRAMFIN", "SIEMENS"
}

FULL_INDIAN_TICKERS = ACTIVE_INDIAN_TICKERS

COMPANY_NAMES = {
    "MSFT": "Microsoft", "AMZN": "Amazon", "TSLA": "Tesla", "GOOGL": "Alphabet (Class A)",
    "GOOG": "Alphabet (Class C)", "UNH": "UnitedHealth", "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil", "JPM": "JPMorgan Chase", "META": "Meta Platforms", "V": "Visa",
    "PG": "Procter & Gamble", "NVDA": "Nvidia", "HD": "Home Depot", "CVX": "Chevron",
    "LLY": "Eli Lilly", "MA": "Mastercard", "ABBV": "AbbVie", "PFE": "Pfizer", "MRK": "Merck",
    "PEP": "PepsiCo", "BAC": "Bank of America", "KO": "Coca-Cola", "COST": "Costco",
    "AVGO": "Broadcom", "TMO": "Thermo Fisher", "WMT": "Walmart", "CSCO": "Cisco",
    "MCD": "McDonald's", "ACN": "Accenture", "ABT": "Abbott", "DIS": "Disney", "DHR": "Danaher",
    "WFC": "Wells Fargo", "BMY": "Bristol Myers Squibb", "LIN": "Linde", "NEE": "NextEra Energy",
    "TXN": "Texas Instruments", "ADBE": "Adobe", "VZ": "Verizon", "CMCSA": "Comcast",
    "PM": "Philip Morris", "COP": "ConocoPhillips", "AMGN": "Amgen", "RTX": "RTX (Raytheon)",
    "HON": "Honeywell", "CRM": "Salesforce",
    "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services", "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank", "ICICIBANK": "ICICI Bank", "SBIN": "State Bank of India",
    "LT": "Larsen & Toubro", "HINDUNILVR": "Hindustan Unilever", "ITC": "ITC Limited",
    "BAJFINANCE": "Bajaj Finance", "ASIANPAINT": "Asian Paints", "HCLTECH": "HCLTech",
    "SUNPHARMA": "Sun Pharmaceutical", "TATAMOTORS": "Tata Motors", "MARUTI": "Maruti Suzuki",
    "KOTAKBANK": "Kotak Mahindra Bank", "TITAN": "Titan Company", "NTPC": "NTPC Limited",
    "POWERGRID": "Power Grid Corp", "AXISBANK": "Axis Bank", "BHARTIARTL": "Bharti Airtel",
    "INDUSINDBK": "IndusInd Bank", "WIPRO": "Wipro", "ULTRACEMCO": "UltraTech Cement",
    "TECHM": "Tech Mahindra", "CIPLA": "Cipla", "NESTLEIND": "Nestle India",
    "TATASTEEL": "Tata Steel", "DRREDDY": "Dr Reddy's Labs", "M&M": "Mahindra & Mahindra",
    "ONGC": "ONGC", "JSWSTEEL": "JSW Steel", "IOC": "Indian Oil", "COALINDIA": "Coal India",
    "GRASIM": "Grasim Industries", "GAIL": "GAIL India", "BRITANNIA": "Britannia",
    "HINDALCO": "Hindalco Industries", "EICHERMOT": "Eicher Motors", "NIFTY200": "Nifty 200",
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports", "APOLLOHOSP": "Apollo Hospitals",
    "BAJAJ-AUTO": "Bajaj Auto", "BANKBARODA": "Bank of Baroda", "BERGEPAINT": "Berger Paints",
    "DIVISLAB": "Divi's Laboratories", "DMART": "Avenue Supermarts", "GODREJCP": "Godrej Consumer Products",
    "HEROMOTOCO": "Hero MotoCorp", "HINDPETRO": "Hindustan Petroleum", "ICICIPRULI": "ICICI Prudential",
    "INDHOTEL": "Indian Hotels", "LTIM": "LTIMindtree", "MUTHOOTFIN": "Muthoot Finance",
    "RECLTD": "REC Ltd", "SRF": "SRF Ltd", "TATACONSUM": "Tata Consumer Products",
    "TATAMOTORS": "Tata Motors", "TATAPOWER": "Tata Power", "TATACHEM": "Tata Chemicals",
    "UPL": "UPL Ltd", "VEDL": "Vedanta", "YESBANK": "Yes Bank", "ZOMATO": "Zomato",
    "TRENT": "Trent Ltd", "BOSCH": "Bosch", "BEL": "Bharat Electronics", "GODREJPROP": "Godrej Properties",
    "HDFCLIFE": "HDFC Life", "HDFCMF": "HDFC Mutual Fund", "ICICIGI": "ICICI Lombard",
    "METROPOLIS": "Metropolis Healthcare", "PAGEIND": "Page Industries", "PIDILITIND": "Pidilite",
    "PERSISTENT": "Persistent Systems", "SHRIRAMFIN": "Shriram Finance", "SIEMENS": "Siemens",
    "TATAGLOBAL": "Tata Global Beverages"
}


def _load_india_market_prices():
    """Load the user-provided Indian archive as a market benchmark when available."""
    frames = []

    india_path = DATA_DIR / "prices" / "stocks_india.csv"
    if india_path.exists():
        frames.append(pd.read_csv(india_path, index_col="Date", parse_dates=True).sort_index())

    if INDIA_ARCHIVE_PATH.exists():
        try:
            archive = pd.read_csv(INDIA_ARCHIVE_PATH, compression="zip")
            archive.columns = [col.strip() for col in archive.columns]
            if {"Date", "Close"}.issubset(archive.columns):
                archive["Date"] = pd.to_datetime(archive["Date"], format="%d-%b-%Y", errors="coerce")
                archive = archive.dropna(subset=["Date"]).sort_values("Date")
                archive = archive.set_index("Date")[["Close"]].rename(columns={"Close": "NIFTY200"})
                frames.append(archive)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, axis=1, join="outer").sort_index()
    combined = combined.apply(pd.to_numeric, errors="coerce")
    return combined.apply(lambda s: s.ffill().bfill())


def _hydrate_missing_india_prices(india_prices):
    """Add active Indian tickers when the local CSV is missing them."""
    missing = [ticker for ticker in sorted(FULL_INDIAN_TICKERS) if ticker not in india_prices.columns]
    if not missing:
        return india_prices

    fetched = []
    for ticker in missing:
        symbol = f"{ticker}.NS" if not ticker.endswith(".NS") else ticker
        try:
            frame = yf.download(symbol, period="2y", auto_adjust=False, progress=False, actions=False)
            if frame.empty:
                continue
            short_name = ticker.replace(".NS", "")
            close = frame[["Close"]].rename(columns={"Close": short_name})
            fetched.append(close)
        except Exception:
            continue

    if not fetched:
        return india_prices

    extra = pd.concat(fetched, axis=1, join="outer").sort_index()
    return pd.concat([india_prices, extra], axis=1, join="outer").sort_index().apply(lambda s: s.ffill().bfill())


def load_prices():
    """Daily closing prices: one row per day, one column per stock from US and Indian markets."""
    us_prices = pd.read_csv(DATA_DIR / "prices" / "stocks.csv", index_col="Date", parse_dates=True)
    us_prices = us_prices.drop(columns="Unnamed: 0").sort_index()

    india_prices = _load_india_market_prices()
    india_prices = _hydrate_missing_india_prices(india_prices)
    if not india_prices.empty:
        prices = pd.concat([us_prices, india_prices], axis=1, join="outer").sort_index()
        return prices.apply(lambda s: s.ffill().bfill())

    return us_prices


def load_financials():
    """Company numbers by year (revenue, profit, ...) plus ratios. Returns a dict of tables."""
    folder = DATA_DIR / "financials"
    tables = {}
    for name in ["revenue", "profit", "assets", "cash", "equity"]:
        table = pd.read_csv(folder / f"data_{name}.csv", index_col=0)
        table.columns = table.columns.astype(int)       # "2022" -> 2022
        tables[name] = table.sort_index(axis=1)         # oldest year first
    tables["stats"] = pd.read_csv(folder / "data_stats.csv", index_col=0)
    tables["valuation"] = pd.read_csv(folder / "data_valuation.csv", index_col=0)
    return tables


def load_news():
    """Financial news sentences, each labelled positive / neutral / negative by people."""
    return pd.read_csv(DATA_DIR / "news" / "all-data.csv", header=None,
                       names=["label", "text"], encoding="latin-1")


def load_economy():
    """Economic indicators (GDP, inflation, ...) for three stock indexes."""
    return pd.read_csv(DATA_DIR / "economy" / "finance_economics_dataset.csv", parse_dates=["Date"])
