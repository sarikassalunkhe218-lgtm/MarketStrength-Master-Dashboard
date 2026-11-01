
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption("Indian Market | Relative Strength | Stage Analysis")

st.warning(
    "Prototype data: Yahoo Finance prices may be delayed, incomplete "
    "or rate-limited. This is not a live trading signal."
)

# Initial Indian stock universe
DEFAULT_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK",
    "INFY", "BHARTIARTL", "ITC", "LT",
    "SBIN", "AXISBANK", "BAJFINANCE", "MARUTI",
    "SUNPHARMA", "TITAN", "TRENT", "BEL",
    "HAL", "ADANIPORTS", "ULTRACEMCO", "NTPC"
]

BENCHMARK = "^NSEI"

@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(symbols):
    tickers = [s + ".NS" for s in symbols] + [BENCHMARK]
    data = yf.download(
        tickers,
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data[["Close"]]

    return close.dropna(axis=1, how="all")

def calculate_rs(prices, ticker):
    if ticker not in prices.columns:
        return None

    series = prices[ticker].dropna()
    if len(series) < 253:
        return None

    current = series.iloc[-1]
    periods = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}

    return {
        period: round((current / series.iloc[-days] - 1) * 100, 2)
        for period, days in periods.items()
    }

menu = st.sidebar.selectbox(
    "Dashboard Sections",
    [
        "Master Dashboard",
        "Relative Strength",
        "Stock Scanner",
        "Import Data"
    ]
)

if menu == "Import Data":
    st.header("Import Your Own Stock Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df, use_container_width=True)

elif menu in ["Master Dashboard", "Relative Strength", "Stock Scanner"]:

    st.header("Indian Stock Relative Strength")

    custom_symbols = st.text_input(
        "Stock symbols (comma separated)",
        value=",".join(DEFAULT_STOCKS)
    )

    symbols = list(dict.fromkeys(
        s.strip().upper()
        for s in custom_symbols.split(",")
        if s.strip()
    ))

    if st.button("Refresh Indian Market Data", type="primary"):
        with st.spinner("Downloading historical prices..."):
            prices = download_prices(tuple(symbols))

        if prices.empty:
            st.error(
                "No price data received. Please try again later."
            )
        else:
            benchmark_data = prices.get(BENCHMARK)

            results = []

            for symbol in symbols:
                ticker = symbol + ".NS"
                rs = calculate_rs(prices, ticker)

                if rs is None or benchmark_data is None:
                    continue

                benchmark_series = benchmark_data.dropna()

                if len(benchmark_series) < 253:
                    continue

                row = {
                    "Symbol": symbol,
                    "1M Return %": rs["1M"],
                    "3M Return %": rs["3M"],
                    "6M Return %": rs["6M"],
                    "12M Return %": rs["12M"],
                    "1M Benchmark %": round(
                        (benchmark_series.iloc[-1] /
                         benchmark_series.iloc[-21] - 1) * 100, 2
                    ),
                    "3M Benchmark %": round(
                        (benchmark_series.iloc[-1] /
                         benchmark_series.iloc[-63] - 1) * 100, 2
                    ),
                    "6M Benchmark %": round(
                        (benchmark_series.iloc[-1] /
                         benchmark_series.iloc[-126] - 1) * 100, 2
                    ),
                    "12M Benchmark %": round(
                        (benchmark_series.iloc[-1] /
                         benchmark_series.iloc[-252] - 1) * 100, 2
                    )
                }

                row["RS 3M vs Nifty"] = round(
                    row["3M Return %"] - row["3M Benchmark %"], 2
                )

                results.append(row)

            if results:
                output = pd.DataFrame(results)
                output = output.sort_values(
                    "RS 3M vs Nifty", ascending=False
                )

                st.success(
                    f"Analysis completed for {len(output)} stocks."
                )

                st.dataframe(
                    output,
                    use_container_width=True,
                    hide_index=True
                )

                csv = output.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "Download RS Results CSV",
                    data=csv,
                    file_name="Indian_Stock_RS.csv",
                    mime="text/csv"
                )
            else:
                st.warning(
                    "Insufficient historical data or unavailable symbols."
                )

    st.caption(
        "Benchmark: Nifty 50. RS figures are historical price returns; "
        "they are not forecasts or recommendations."
    )

