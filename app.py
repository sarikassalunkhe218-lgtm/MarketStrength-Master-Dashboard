
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
st.caption("Indian Market | Nifty 500 | Sector Rotation | Relative Strength")

st.warning(
    "Yahoo Finance data may be delayed, incomplete or rate-limited. "
    "This dashboard is for research, not automatic trading."
)

BENCHMARK = "^NSEI"

SECTOR_INDICES = {
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty Auto": "^CNXAUTO",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Media": "^CNXMEDIA",
    "Nifty PSU Bank": "^CNXPSUBANK",
    "Nifty Financial Services": "^CNXFIN",
    "Nifty Healthcare": "^CNXHEALTHCARE",
    "Nifty Oil & Gas": "^CNXENERGY",
    "Nifty Consumer Durables": "^CNXCONSUMERDURABLES"
}

@st.cache_data(ttl=86400)
def get_nifty500():
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))
    df.columns = df.columns.str.strip()

    symbol_col = next(
        (c for c in df.columns if c.lower() == "symbol"),
        None
    )

    sector_col = next(
        (c for c in df.columns if c.lower() == "industry"),
        None
    )

    if symbol_col is None:
        raise ValueError("Nifty 500 Symbol column not found.")

    if sector_col is None:
        raise ValueError("Nifty 500 Industry column not found.")

    df = df[[symbol_col, sector_col]].dropna()
    df.columns = ["Symbol", "Sector"]

    df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
    df["Sector"] = df["Sector"].astype(str).str.strip()

    return df

@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(tickers):
    data = yf.download(
        list(tickers),
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
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "12M": 252
    }

    result = {}

    for label, days in periods.items():
        result[label] = (
            series.iloc[-1] / series.iloc[-days] - 1
        ) * 100

    return result

@st.cache_data(ttl=3600)
def run_stock_scanner(symbols):
    tickers = [s + ".NS" for s in symbols] + [BENCHMARK]
    prices = download_prices(tuple(tickers))

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

        for period in ["1M", "3M", "6M", "12M"]:
            row[period + " Return %"] = round(returns[period], 2)
            row[period + " RS vs Nifty"] = round(
                returns[period] - benchmark[period], 2
            )

        results.append(row)

    if not results:
        return pd.DataFrame()

    output = pd.DataFrame(results)

    return output.sort_values(
        "3M RS vs Nifty", ascending=False
    ).reset_index(drop=True)

@st.cache_data(ttl=3600)
def run_sector_scanner():
    tickers = list(set(SECTOR_INDICES.values()) | {BENCHMARK})
    prices = download_prices(tuple(tickers))

    if prices.empty or BENCHMARK not in prices.columns:
        return pd.DataFrame()

    benchmark = calculate_returns(prices[BENCHMARK])

    if benchmark is None:
        return pd.DataFrame()

    results = []

    for sector, ticker in SECTOR_INDICES.items():
        if ticker not in prices.columns:
            continue

        returns = calculate_returns(prices[ticker])

        if returns is None:
            continue

        row = {"Sector": sector}

        for period in ["1M", "3M", "6M", "12M"]:
            row[period + " Return %"] = round(returns[period], 2)
            row[period + " RS vs Nifty"] = round(
                returns[period] - benchmark[period], 2
            )

        row["RS Momentum"] = round(
            row["3M RS vs Nifty"] - row["6M RS vs Nifty"], 2
        )

        results.append(row)

    if not results:
        return pd.DataFrame()

    output = pd.DataFrame(results)

    rs = output["3M RS vs Nifty"]
    momentum = output["RS Momentum"]

    rs_mid = rs.median()
    momentum_mid = momentum.median()

    def classify(row):
        strong = row["3M RS vs Nifty"] >= rs_mid
        improving = row["RS Momentum"] >= momentum_mid

        if strong and improving:
            return "Leading"
        if not strong and improving:
            return "Improving"
        if strong and not improving:
            return "Weakening"
        return "Lagging"

    output["Rotation Stage"] = output.apply(classify, axis=1)

    return output.sort_values(
        "3M RS vs Nifty", ascending=False
    ).reset_index(drop=True)

menu = st.sidebar.selectbox(
    "Dashboard Sections",
    [
        "Master Dashboard",
        "Sector Rotation",
        "Nifty 500 Scanner",
        "Import Data"
    ]
)

if menu == "Import Data":
    st.header("Import Your Own Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df, use_container_width=True)

elif menu == "Sector Rotation":
    st.header("NSE Sector Rotation")

    if st.button("Run Sector Rotation", type="primary"):
        with st.spinner("Downloading sector index data..."):
            sectors = run_sector_scanner()

        if sectors.empty:
            st.error(
                "Sector data unavailable. Some Yahoo Finance index "
                "symbols may not be supported."
            )
        else:
            st.success(
                f"Sector analysis completed for {len(sectors)} indices."
            )

            counts = sectors["Rotation Stage"].value_counts()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Leading", counts.get("Leading", 0))
            c2.metric("Improving", counts.get("Improving", 0))
            c3.metric("Weakening", counts.get("Weakening", 0))
            c4.metric("Lagging", counts.get("Lagging", 0))

            st.subheader("Sector Rotation Rankings")

            st.dataframe(
                sectors,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Sector Rotation CSV",
                sectors.to_csv(index=False).encode("utf-8"),
                "Sector_Rotation.csv",
                "text/csv"
            )

elif menu == "Nifty 500 Scanner":
    st.header("Nifty 500 Relative Strength Scanner")

    if st.button("Load Nifty 500 & Run Scanner", type="primary"):
        try:
            with st.spinner("Loading Nifty 500 constituents..."):
                universe = get_nifty500()

            st.success(f"Loaded {len(universe)} stocks.")

            with st.spinner("Calculating stock relative strength..."):
                output = run_stock_scanner(
                    tuple(universe["Symbol"].tolist())
                )

            if output.empty:
                st.error("No usable stock price data received.")
            else:
                output = output.merge(
                    universe,
                    on="Symbol",
                    how="left"
                )

                st.success(f"Analysed {len(output)} stocks.")

                st.dataframe(
                    output,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "Download Nifty 500 Results",
                    output.to_csv(index=False).encode("utf-8"),
                    "Nifty500_RS_Results.csv",
                    "text/csv"
                )

        except Exception as error:
            st.error("Scanner could not complete.")
            st.code(str(error))

else:
    st.header("MarketStrength Master Dashboard")

    st.write("Your Indian market analysis workspace.")

    st.markdown("""
    **Analysis workflow**

    1. Market Trend
    2. Sector Rotation
    3. Strong Stocks
    4. Stage Analysis
    5. Fundamentals
    6. Entry Candidates
    """)

    st.info(
        "Use the Sector Rotation and Nifty 500 Scanner pages "
        "to run the current analysis."
    )

st.caption(
    "MarketStrength Master Dashboard | Historical data research tool"
)
