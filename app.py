
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
st.caption("Indian Market | Nifty 500 | Sector Rotation | Stage Analysis")

st.warning(
    "Yahoo Finance data may be delayed, incomplete or rate-limited. "
    "This dashboard is for research, not automatic trading."
    "Historical Yahoo Finance data may be delayed, incomplete or rate-limited. "
    "Signals are research classifications, not investment advice."
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
    "Nifty Healthcare": "^CNXHEALTHCARE"
}

# ---------- COLOUR FORMATTING ----------

STAGE_COLORS = {
    "Stage 1 - Basing": "background-color: #FFF2CC; color: #7F6000",
    "Stage 2 - Advancing": "background-color: #D9EAD3; color: #274E13",
    "Stage 3 - Topping": "background-color: #FCE4D6; color: #984807",
    "Stage 4 - Declining": "background-color: #F4CCCC; color: #990000"
}

ROTATION_COLORS = {
    "Leading": "background-color: #D9EAD3; color: #274E13",
    "Improving": "background-color: #D9EAF7; color: #073763",
    "Weakening": "background-color: #FCE4D6; color: #984807",
    "Lagging": "background-color: #F4CCCC; color: #990000"
}

def colour_stage(value):
    return STAGE_COLORS.get(value, "")

def colour_rotation(value):
    return ROTATION_COLORS.get(value, "")

# ---------- NIFTY 500 UNIVERSE ----------

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
        df["Industry"] = "Not available"
        sector_col = "Industry"

    df = df[[symbol_col, sector_col]].dropna()
    df = df[[symbol_col, sector_col]].dropna(subset=[symbol_col])
    df.columns = ["Symbol", "Sector"]

    df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
    df["Sector"] = df["Sector"].astype(str).str.strip()

    return df

# ---------- PRICE DOWNLOAD ----------

@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(tickers):
def download_prices(tickers, period="2y", interval="1d"):
    data = yf.download(
        list(tickers),
        period="2y",
        interval="1d",
        period=period,
        interval=interval,
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

# ---------- RELATIVE STRENGTH ----------

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
    return {
        period: (
            series.iloc[-1] / series.iloc[-days] - 1
        ) * 100

    return result
        for period, days in periods.items()
    }

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

# ---------- SECTOR ROTATION ----------

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
    rs_mid = output["3M RS vs Nifty"].median()
    momentum_mid = output["RS Momentum"].median()

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

# ---------- WEINSTEIN STAGE ANALYSIS ----------

@st.cache_data(ttl=3600, show_spinner=False)
def run_stage_scanner(symbols):
    tickers = [symbol + ".NS" for symbol in symbols]

    weekly = download_prices(
        tuple(tickers),
        period="5y",
        interval="1wk"
    )

    if weekly.empty:
        return pd.DataFrame()

    results = []

    for symbol in symbols:
        ticker = symbol + ".NS"

        if ticker not in weekly.columns:
            continue

        prices = weekly[ticker].dropna()

        if len(prices) < 40:
            continue

        ma30 = prices.rolling(30).mean().dropna()

        if len(ma30) < 5:
            continue

        current_price = prices.iloc[-1]
        current_ma = ma30.iloc[-1]
        previous_ma = ma30.iloc[-5]

        slope_pct = (
            (current_ma / previous_ma) - 1
        ) * 100

        distance_pct = (
            (current_price / current_ma) - 1
        ) * 100

        if current_price > current_ma and slope_pct > 0:
            stage = "Stage 2 - Advancing"
        elif current_price < current_ma and slope_pct < 0:
            stage = "Stage 4 - Declining"
        elif current_price > current_ma and slope_pct <= 0:
            stage = "Stage 3 - Topping"
        else:
            stage = "Stage 1 - Basing"

        results.append({
            "Symbol": symbol,
            "Last Price": round(float(current_price), 2),
            "30-Week MA": round(float(current_ma), 2),
            "Price vs MA %": round(float(distance_pct), 2),
            "MA Slope % (4 weeks)": round(float(slope_pct), 2),
            "Stage": stage
        })

    return pd.DataFrame(results)

# ---------- SIDEBAR ----------

menu = st.sidebar.selectbox(
    "Dashboard Sections",
    [
        "Master Dashboard",
        "Sector Rotation",
        "Nifty 500 Scanner",
        "Stage Analysis",
        "Import Data"
    ]
)

# ---------- IMPORT DATA ----------

if menu == "Import Data":
    st.header("Import Your Own Data")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df, use_container_width=True)

# ---------- SECTOR ROTATION PAGE ----------

elif menu == "Sector Rotation":
    st.header("NSE Sector Rotation")
    st.caption("Green = Leading | Blue = Improving | Orange = Weakening | Red = Lagging")

    if st.button("Run Sector Rotation", type="primary"):
        with st.spinner("Downloading sector index data..."):
            sectors = run_sector_scanner()

        if sectors.empty:
            st.error(
                "Sector data unavailable. Some Yahoo Finance index "
                "symbols may not be supported."
            )
            st.error("Sector data unavailable. Please try again later.")
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
            styled = sectors.style.map(
                colour_rotation,
                subset=["Rotation Stage"]
            )

            st.dataframe(
                sectors,
                styled,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Sector Rotation CSV",
                sectors.to_csv(index=False).encode("utf-8"),
                "Sector_Rotation.csv",
                "text/csv"
            )

# ---------- NIFTY 500 PAGE ----------

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

# ---------- STAGE ANALYSIS PAGE ----------

elif menu == "Stage Analysis":
    st.header("Weinstein Stage Analysis")
    st.caption(
        "Weekly charts | 30-week moving average | "
        "Green = Stage 2, Yellow = Stage 1, Orange = Stage 3, Red = Stage 4"
    )

    if st.button("Run Nifty 500 Stage Analysis", type="primary"):
        try:
            with st.spinner("Loading Nifty 500 universe..."):
                universe = get_nifty500()

            st.success(f"Loaded {len(universe)} stocks.")

            with st.spinner(
                "Downloading weekly prices and calculating stages. "
                "This may take several minutes..."
            ):
                stages = run_stage_scanner(
                    tuple(universe["Symbol"].tolist())
                )

            if stages.empty:
                st.error("No usable weekly price data received.")
            else:
                counts = stages["Stage"].value_counts()

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Stage 1 - Basing", counts.get("Stage 1 - Basing", 0))
                c2.metric("Stage 2 - Advancing", counts.get("Stage 2 - Advancing", 0))
                c3.metric("Stage 3 - Topping", counts.get("Stage 3 - Topping", 0))
                c4.metric("Stage 4 - Declining", counts.get("Stage 4 - Declining", 0))

                stages = stages.merge(
                    universe,
                    on="Symbol",
                    how="left"
                )

                stages = stages[
                    ["Symbol", "Sector", "Last Price", "30-Week MA",
                     "Price vs MA %", "MA Slope % (4 weeks)", "Stage"]
                ]

                stages = stages.sort_values(
                    "MA Slope % (4 weeks)",
                    ascending=False
                )

                styled = stages.style.map(
                    colour_stage,
                    subset=["Stage"]
                )

                st.subheader("Stage Analysis Results")

                st.dataframe(
                    styled,
                    use_container_width=True,
                    hide_index=True
                )

                stage2 = stages[
                    stages["Stage"] == "Stage 2 - Advancing"
                ]

                st.subheader("Potential Stage 2 Candidates")
                st.dataframe(
                    stage2,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "Download Stage Analysis CSV",
                    stages.to_csv(index=False).encode("utf-8"),
                    "Nifty500_Stage_Analysis.csv",
                    "text/csv"
                )

        except Exception as error:
            st.error("Stage analysis could not complete.")
            st.code(str(error))

# ---------- MASTER DASHBOARD ----------

else:
    st.header("MarketStrength Master Dashboard")

    st.write("Your Indian market analysis workspace.")

    st.markdown("""
    **Analysis workflow**
    ### Analysis workflow

    1. Market Trend
    2. Sector Rotation
    3. Strong Stocks
    4. Stage Analysis
    5. Fundamentals
    6. Entry Candidates
    """)

    st.markdown("""
    ### Stage colour guide

    - 🟡 Stage 1 — Basing / Accumulation
    - 🟢 Stage 2 — Advancing / Uptrend
    - 🟠 Stage 3 — Topping / Distribution
    - 🔴 Stage 4 — Declining / Downtrend
    """)

    st.info(
        "Use the Sector Rotation and Nifty 500 Scanner pages "
        "to run the current analysis."
        "Run Sector Rotation, Nifty 500 Scanner and Stage Analysis "
        "from the sidebar to view the current research results."
    )

st.caption(
    "MarketStrength Master Dashboard | Historical data research tool"
)

