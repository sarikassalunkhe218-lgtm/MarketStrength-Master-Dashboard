
import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption(
    "Indian and Global Markets | Relative Strength | "
    "Sector Rotation | Stage Analysis"
)


# --------------------------------------------------
# MARKET UNIVERSES
# --------------------------------------------------

US_STOCKS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "LLY": "Eli Lilly",
    "JPM": "JPMorgan Chase",
    "COST": "Costco"
}

INDIAN_ETFS = {
    "NIFTYBEES.NS": "Nifty 50 ETF",
    "JUNIORBEES.NS": "Nifty Next 50 ETF",
    "MONQ50.NS": "MONQ50 ETF",
    "GOLDBEES.NS": "Gold ETF"
}

GLOBAL_ETFS = {
    "VWRA.L": "Vanguard FTSE All-World ETF",
    "CSPX.L": "iShares Core S&P 500 ETF",
    "AGAC.L": "Global Aggregate Bond ETF"
}

SECTOR_ETFS = {
    "BANKBEES.NS": "Banking",
    "ITBEES.NS": "Information Technology",
    "PHARMABEES.NS": "Pharma",
    "AUTOETF.NS": "Automobile",
    "CPSEETF.NS": "PSU / CPSE"
}


# --------------------------------------------------
# DOWNLOAD NIFTY 500 CONSTITUENTS
# --------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def get_nifty500():

    url = (
        "https://www.niftyindices.com/"
        "IndexConstituent/ind_nifty500list.csv"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,*/*"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))
    df.columns = df.columns.str.strip()

    if "Symbol" not in df.columns:
        raise ValueError(
            "The downloaded file does not contain a Symbol column."
        )

    company_column = (
        "Company Name"
        if "Company Name" in df.columns
        else "Symbol"
    )

    df = df.dropna(subset=["Symbol"])

    df["Symbol"] = (
        df["Symbol"].astype(str).str.strip()
    )

    df[company_column] = (
        df[company_column].astype(str).str.strip()
    )

    df = df.drop_duplicates(subset=["Symbol"])

    return dict(
        zip(df["Symbol"], df[company_column])
    )


# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

st.sidebar.title("Market Settings")

market = st.sidebar.selectbox(
    "Select Market",
    [
        "India",
        "United States",
        "Indian ETFs",
        "Global ETFs"
    ]
)

page = st.sidebar.radio(
    "Dashboard Section",
    [
        "Master Dashboard",
        "Sector Rotation",
        "Stock Scanner",
        "Stage Analysis",
        "Fundamentals / Import Data"
    ]
)


# --------------------------------------------------
# SELECT ASSET UNIVERSE
# --------------------------------------------------

assets = {}

if market == "India":

    try:
        with st.spinner("Loading Nifty 500 constituents..."):
            assets = get_nifty500()

        st.sidebar.success(
            f"Nifty 500 loaded: {len(assets)} stocks"
        )

    except Exception as error:
        st.sidebar.error("Could not load Nifty 500 list.")
        st.sidebar.caption(str(error))

elif market == "United States":
    assets = US_STOCKS

elif market == "Indian ETFs":
    assets = INDIAN_ETFS

else:
    assets = GLOBAL_ETFS


st.sidebar.info(
    "Price data is provided by Yahoo Finance where available."
)


# --------------------------------------------------
# TICKER CONVERSION
# --------------------------------------------------

def yahoo_ticker(ticker, market_name):

    if market_name == "India":
        return ticker + ".NS"

    if market_name == "United States":
        return ticker

    return ticker


# --------------------------------------------------
# PRICE DOWNLOAD IN SMALL BATCHES
# --------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def download_close_prices(tickers):

    close_data = {}

    batch_size = 25

    for start in range(0, len(tickers), batch_size):

        batch = list(tickers[start:start + batch_size])

        try:

            data = yf.download(
                tickers=batch,
                period="2y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=False
            )

            if data is None or data.empty:
                continue

            for ticker in batch:

                try:

                    if isinstance(data.columns, pd.MultiIndex):

                        if ticker in data.columns.get_level_values(0):

                            close = data[ticker]["Close"]

                        elif ticker in data.columns.get_level_values(1):

                            ticker_data = data.xs(
                                ticker,
                                axis=1,
                                level=1
                            )

                            close = ticker_data["Close"]

                        else:
                            continue

                    else:

                        if len(batch) != 1:
                            continue

                        close = data["Close"]

                    if isinstance(close, pd.DataFrame):
                        close = close.iloc[:, 0]

                    close = pd.to_numeric(
                        close,
                        errors="coerce"
                    ).dropna()

                    if not close.empty:
                        close_data[ticker] = close

                except Exception:
                    continue

        except Exception:
            continue

    return close_data


# --------------------------------------------------
# STAGE CLASSIFICATION
# --------------------------------------------------

def stage_label(close):

    if len(close) < 170:
        return "Insufficient Data"

    ma150 = close.rolling(150).mean()

    current_price = close.iloc[-1]
    current_ma = ma150.iloc[-1]
    previous_ma = ma150.iloc[-20]

    if pd.isna(current_ma) or pd.isna(previous_ma):
        return "Insufficient Data"

    if current_price > current_ma and current_ma > previous_ma:
        return "Stage 2"

    if current_price < current_ma and current_ma < previous_ma:
        return "Stage 4"

    if current_price > current_ma and current_ma <= previous_ma:
        return "Stage 3"

    return "Stage 1"


# --------------------------------------------------
# RETURNS
# --------------------------------------------------

def calculate_return(close, days):

    if len(close) <= days:
        return None

    old_price = close.iloc[-days - 1]
    current_price = close.iloc[-1]

    if old_price == 0:
        return None

    return round(
        (current_price / old_price - 1) * 100,
        2
    )


# --------------------------------------------------
# BUILD STOCK SCANNER TABLE
# --------------------------------------------------

def build_market_table(asset_list, market_name):

    if not asset_list:
        return pd.DataFrame(), 0

    original_tickers = list(asset_list.keys())

    converted_tickers = [
        yahoo_ticker(ticker, market_name)
        for ticker in original_tickers
    ]

    with st.spinner(
        f"Downloading prices for {len(converted_tickers)} assets..."
    ):

        prices = download_close_prices(
            tuple(converted_tickers)
        )

    rows = []

    for original, ticker in zip(
        original_tickers,
        converted_tickers
    ):

        close = prices.get(ticker)

        if close is None or close.empty:
            continue

        last_price = float(close.iloc[-1])

        stage = stage_label(close)

        return_1m = calculate_return(close, 21)
        return_3m = calculate_return(close, 63)
        return_6m = calculate_return(close, 126)
        return_12m = calculate_return(close, 252)

        if (
            stage == "Stage 2"
            and return_3m is not None
            and return_3m > 0
        ):
            signal = "BUY CANDIDATE"
        else:
            signal = "WATCH"

        rows.append({
            "Ticker": original,
            "Company / ETF": asset_list[original],
            "Price": round(last_price, 2),
            "1M Return %": return_1m,
            "3M Return %": return_3m,
            "6M Return %": return_6m,
            "12M Return %": return_12m,
            "Stage": stage,
            "Signal": signal
        })

    result = pd.DataFrame(rows)

    return result, len(prices)


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

def show_table(df, total_assets=None, loaded_assets=None):

    if df.empty:

        st.warning(
            "No price data was returned. "
            "Please try again later."
        )

        return

    if total_assets is not None:

        st.write(
            f"Showing **{len(df)}** assets with usable price data "
            f"out of **{total_assets}** requested."
        )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Results as CSV",
        data=csv_data,
        file_name="marketstrength_results.csv",
        mime="text/csv"
    )


# --------------------------------------------------
# MASTER DASHBOARD
# --------------------------------------------------

if page == "Master Dashboard":

    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Selected Market", market)

    col2.metric(
        "Assets in Universe",
        len(assets)
    )

    col3.metric(
        "Return Periods",
        "1M / 3M / 6M / 12M"
    )

    col4.metric(
        "Updated",
        datetime.now().strftime("%d %b %Y")
    )

    st.markdown("### Market Strength Scanner")

    st.write(
        "Review price performance, relative momentum "
        "and approximate market stages."
    )

    df, loaded = build_market_table(assets, market)

    show_table(
        df,
        total_assets=len(assets),
        loaded_assets=loaded
    )


# --------------------------------------------------
# SECTOR ROTATION
# --------------------------------------------------

elif page == "Sector Rotation":

    st.subheader("Indian Sector Rotation")

    st.write(
        "This starter sector screen uses ETF price returns. "
        "It is not yet a complete benchmark-relative RS model."
    )

    df, loaded = build_market_table(
        SECTOR_ETFS,
        "Indian ETFs"
    )

    if not df.empty:

        def rotation_label(row):

            r1 = row["1M Return %"]
            r3 = row["3M Return %"]

            if pd.isna(r1) or pd.isna(r3):
                return "Insufficient Data"

            if r1 > 0 and r3 > 0:
                return "Leading"

            if r1 > 0 and r3 <= 0:
                return "Improving"

            if r1 <= 0 and r3 > 0:
                return "Weakening"

            return "Lagging"

        df["Rotation"] = df.apply(
            rotation_label,
            axis=1
        )

    show_table(df)


# --------------------------------------------------
# STOCK SCANNER
# --------------------------------------------------

elif page == "Stock Scanner":

    st.subheader(f"{market} Stock Scanner")

    st.write(
        "Stocks are ranked by their 3-month price return. "
        "Missing price data is excluded from the ranking."
    )

    df, loaded = build_market_table(
        assets,
        market
    )

    if not df.empty:

        df = df.sort_values(
            "3M Return %",
            ascending=False,
            na_position="last"
        )

        show_table(
            df,
            total_assets=len(assets),
            loaded_assets=loaded
        )


# --------------------------------------------------
# STAGE ANALYSIS
# --------------------------------------------------

elif page == "Stage Analysis":

    st.subheader("Stage 1–4 Analysis")

    st.info(
        "This is an approximate daily-price stage screen "
        "using a 150-day moving average. "
        "It is not a full weekly Weinstein stage analysis."
    )

    df, loaded = build_market_table(
        assets,
        market
    )

    if not df.empty:

        stage_df = df[
            [
                "Ticker",
                "Company / ETF",
                "Price",
                "Stage",
                "Signal"
            ]
        ]

        show_table(
            stage_df,
            total_assets=len(assets),
            loaded_assets=loaded
        )


# --------------------------------------------------
# FUNDAMENTALS / IMPORT DATA
# --------------------------------------------------

elif page == "Fundamentals / Import Data":

    st.subheader("Fundamentals / Import Data")

    st.write(
        "Download the template, enter your fundamental data "
        "and upload the completed CSV file."
    )

    template = pd.DataFrame(columns=[
        "Ticker",
        "Company",
        "Market Cap",
        "Sales Growth %",
        "Profit Growth %",
        "ROE %",
        "ROCE %",
        "Debt / Equity",
        "Promoter Pledge %",
        "P/E"
    ])

    st.download_button(
        "Download Fundamentals CSV Template",
        data=template.to_csv(index=False).encode("utf-8"),
        file_name="fundamentals_template.csv",
        mime="text/csv"
    )

    uploaded = st.file_uploader(
        "Upload your fundamentals CSV",
        type=["csv"]
    )

    if uploaded is not None:

        try:

            fundamental_df = pd.read_csv(uploaded)

            st.success("CSV uploaded successfully.")

            st.dataframe(
                fundamental_df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Imported Fundamentals",
                data=fundamental_df.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="imported_fundamentals.csv",
                mime="text/csv"
            )

        except Exception as error:

            st.error(
                f"Could not read the CSV file: {error}"
            )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "MarketStrength Dashboard | Yahoo Finance price data "
    "| Simplified screening indicators | "
    "For research and educational purposes"
)
