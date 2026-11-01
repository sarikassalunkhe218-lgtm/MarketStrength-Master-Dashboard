
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from io import StringIO

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption("Indian Stocks | Nifty 500 | Relative Strength")

st.warning(
    "Yahoo Finance data may be delayed, incomplete or rate-limited. "
    "This dashboard is for research, not automatic trading."
)

BENCHMARK = "^NSEI"

@st.cache_data(ttl=86400)
def get_nifty500():
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,*/*"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))
    df.columns = df.columns.str.strip()

    symbol_col = next(
        (c for c in df.columns if c.lower() == "symbol"),
        None
    )

    if symbol_col is None:
        raise ValueError("Symbol column not found in Nifty 500 file.")

    symbols = (
        df[symbol_col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

    return symbols

@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(symbols):
    tickers = [s + ".NS" for s in symbols] + [BENCHMARK]

    data = yf.download(
        tickers,
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column"
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            return pd.DataFrame()
        close = data["Close"]
    else:
        if "Close" not in data.columns:
            return pd.DataFrame()
        close = data[["Close"]]

    return close.dropna(axis=1, how="all")

def calculate_returns(series):
    series = series.dropna()

    if len(series) < 253:
        return None

    periods = {
        "1M Return %": 21,
        "3M Return %": 63,
        "6M Return %": 126,
        "12M Return %": 252
    }

    result = {}

    for label, days in periods.items():
        result[label] = round(
            (series.iloc[-1] / series.iloc[-days] - 1) * 100,
            2
        )

    return result

@st.cache_data(ttl=3600)
def run_scanner(symbols):
    prices = download_prices(tuple(symbols))

    if prices.empty or BENCHMARK not in prices.columns:
        return pd.DataFrame()

    benchmark = calculate_returns(prices[BENCHMARK])

    if benchmark is None:
        return pd.DataFrame()

    results = []

    for symbol in symbols:
        ticker = symbol + ".NS"

        if ticker not in prices.columns:
            continue

        returns = calculate_returns(prices[ticker])

        if returns is None:
            continue

        row = {"Symbol": symbol}
        row.update(returns)

        for period, days in [
            ("1M", 21),
            ("3M", 63),
            ("6M", 126),
            ("12M", 252)
        ]:
            stock_return = row[period + " Return %"]
            benchmark_return = benchmark[period + " Return %"]

            row[period + " RS vs Nifty"] = round(
                stock_return - benchmark_return, 2
            )

        results.append(row)

    if not results:
        return pd.DataFrame()

    output = pd.DataFrame(results)

    output = output.sort_values(
        "3M RS vs Nifty",
        ascending=False
    ).reset_index(drop=True)

    output.insert(0, "Rank", range(1, len(output) + 1))

    return output

menu = st.sidebar.selectbox(
    "Dashboard Sections",
    [
        "Master Dashboard",
        "Nifty 500 Scanner",
        "Relative Strength",
        "Import Data"
    ]
)

if menu == "Import Data":
    st.header("Import Your Own Data")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df, use_container_width=True)

else:
    st.header("Nifty 500 Relative Strength Scanner")

    st.write(
        "Automatically loads the Nifty 500 stock universe "
        "and ranks stocks by relative strength."
    )

    if st.button("Load Nifty 500 & Run Scanner", type="primary"):

        try:
            with st.spinner("Loading official Nifty 500 stock list..."):
                symbols = get_nifty500()

            st.success(
                f"Loaded {len(symbols)} Nifty 500 constituents."
            )

            with st.spinner(
                "Downloading historical prices and calculating RS. "
                "This may take several minutes..."
            ):
                output = run_scanner(tuple(symbols))

            if output.empty:
                st.error(
                    "No usable price data was returned. "
                    "Please try again later."
                )
            else:
                st.success(
                    f"Scanner completed: {len(output)} stocks analysed."
                )

                st.metric("Stocks Analysed", len(output))

                st.subheader("Strongest Stocks")

                st.dataframe(
                    output,
                    use_container_width=True,
                    hide_index=True
                )

                csv = output.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "Download Nifty 500 RS Results",
                    data=csv,
                    file_name="Nifty500_RS_Results.csv",
                    mime="text/csv"
                )

        except Exception as error:
            st.error("Scanner could not complete.")
            st.code(str(error))

    st.caption(
        "Benchmark: Nifty 50 (^NSEI). Rankings use historical "
        "price returns and are not investment recommendations."
    )
