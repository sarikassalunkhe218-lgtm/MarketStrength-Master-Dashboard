
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import io
import requests

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption("Indian and Global Markets | Relative Strength | Stage Analysis")

# Sidebar
st.sidebar.header("Market Settings")
market = st.sidebar.selectbox(
    "Select Market",
    ["India", "United States", "Global ETFs", "Indian ETFs"]
)

st.sidebar.info(
    "This dashboard uses downloaded market data or your own CSV file. "
    "Signals are educational screening results, not investment advice."
)


# NIFTY 500 UNIVERSE
@st.cache_data(ttl=86400, show_spinner=False)
def get_nifty500():
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,*/*"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))
    df.columns = df.columns.str.strip()

    if "Symbol" not in df.columns:
        raise ValueError("Nifty 500 CSV does not contain a Symbol column.")

    company_column = (
        "Company Name" if "Company Name" in df.columns else "Symbol"
    )

    df = df.dropna(subset=["Symbol"])

    return dict(zip(
        df["Symbol"].astype(str).str.strip(),
        df[company_column].astype(str).str.strip()
    ))

# Other starter universes
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

# Select market universe
if market == "India":
    try:
        assets = get_nifty500()
        st.sidebar.success(f"Nifty 500 loaded: {len(assets)} stocks")
    except Exception as error:
        assets = {}
        st.sidebar.error("Could not download Nifty 500 list.")
        st.sidebar.caption(str(error))

elif market == "United States":
    assets = US_STOCKS
elif market == "Indian ETFs":
    assets = INDIAN_ETFS
else:
    assets = GLOBAL_ETFS


# Sidebar pages
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

@st.cache_data(ttl=1800, show_spinner=False)
def get_prices(tickers):
    data = yf.download(
        tickers=list(tickers),
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True
    )
    return data

def extract_close(data, ticker):
    try:
        if isinstance(data.columns, pd.MultiIndex):
            close = data[ticker]["Close"]
        else:
            close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.dropna()
    except Exception:
        return pd.Series(dtype=float)

def stage_label(close):
    if len(close) < 160:
        return "Insufficient Data"
    ma30 = close.rolling(150).mean()
    current = close.iloc[-1]
    average = ma30.iloc[-1]
    previous = ma30.iloc[-20]
    if current > average and average > previous:
        return "Stage 2"
    if current < average and average < previous:
        return "Stage 4"
    if current > average and average <= previous:
        return "Stage 3"
    return "Stage 1"

def build_market_table(assets, market_name):
    tickers = list(assets.keys())
    if not tickers:
        return pd.DataFrame()

    yf_tickers = [
        t if t.endswith(".NS") or "." in t or market_name == "United States"
        else t + ".NS"
        for t in tickers
    ]

    with st.spinner("Downloading market prices. Please wait..."):
        prices = get_prices(tuple(yf_tickers))

    rows = []
    for original, ticker in zip(tickers, yf_tickers):
        close = extract_close(prices, ticker)
        if close.empty:
            continue

        last = float(close.iloc[-1])
        def ret(days):
            if len(close) <= days:
                return None
            return round((last / float(close.iloc[-days-1]) - 1) * 100, 2)

        rows.append({
            "Ticker": original,
            "Company / ETF": assets[original],
            "Price": round(last, 2),
            "1M RS %": ret(21),
            "3M RS %": ret(63),
            "6M RS %": ret(126),
            "12M RS %": ret(252),
            "Stage": stage_label(close),
            "Signal": (
                "BUY CANDIDATE"
                if stage_label(close) == "Stage 2" and ret(63) is not None and ret(63) > 0
                else "WATCH"
            )
        })

    return pd.DataFrame(rows)

def show_table(df):
    if df.empty:
        st.warning(
            "No market data returned. Try again later, or use the CSV Import section."
        )
        return

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download results as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="marketstrength_results.csv",
        mime="text/csv"
    )

if page == "Master Dashboard":
    st.subheader("Market Overview")
    a, b, c, d = st.columns(4)
    a.metric("Selected Market", market)
    b.metric("Assets in Starter List", len(assets))
    c.metric("Analysis", "1M / 3M / 6M / 12M")
    d.metric("Updated", datetime.now().strftime("%d %b %Y"))

    st.markdown("### Market Strength Scanner")
    st.write(
        "Compare price performance, identify Stage 2 candidates, "
        "and review the strongest assets in the selected list."
    )
    df = build_market_table(assets, market)
    show_table(df)

elif page == "Sector Rotation":
    st.subheader("Sector Rotation")
    st.write(
        "This starter page compares a small selection of Indian sector ETFs. "
        "Rotation labels are based on recent price performance, not a full "
        "benchmark-relative sector rotation model."
    )
    sectors = {
        "BANKBEES.NS": "Banking",
        "ITBEES.NS": "Information Technology",
        "PHARMABEES.NS": "Pharma",
        "AUTOETF.NS": "Automobile",
        "CPSEETF.NS": "PSU / CPSE"
    }
    sector_df = build_market_table(sectors, "India")
    if not sector_df.empty:
        def rotation(row):
            r1 = row["1M RS %"]
            r3 = row["3M RS %"]
            if pd.isna(r1) or pd.isna(r3):
                return "Insufficient Data"
            if r1 > 0 and r3 > 0:
                return "Leading"
            if r1 > 0 and r3 <= 0:
                return "Improving"
            if r1 <= 0 and r3 > 0:
                return "Weakening"
            return "Lagging"
        sector_df["Rotation"] = sector_df.apply(rotation, axis=1)
    show_table(sector_df)

elif page == "Stock Scanner":
    st.subheader("Stock Scanner")
    st.write("Scan the starter list for positive momentum and Stage 2.")
    df = build_market_table(assets, market)
    if not df.empty:
        df = df.sort_values("3M RS %", ascending=False, na_position="last")
        show_table(df)

elif page == "Stage Analysis":
    st.subheader("Stage Analysis")
    st.write(
        "Approximate stage classification using price and a 150-day moving average. "
        "This is a simplified screen, not a complete weekly-chart stage analysis."
    )
    df = build_market_table(assets, market)
    if not df.empty:
        show_table(df[["Ticker", "Company / ETF", "Price", "Stage", "Signal"]])

else:
    st.subheader("Fundamentals / Import Data")
    st.write(
        "Upload a CSV containing your own fundamental data. "
        "This page does not automatically retrieve company fundamentals yet."
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

    uploaded = st.file_uploader("Upload your fundamentals CSV", type=["csv"])
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
                "Download imported data",
                data=fundamental_df.to_csv(index=False).encode("utf-8"),
                file_name="imported_fundamentals.csv",
                mime="text/csv"
            )
        except Exception as exc:
            st.error(f"Could not read this CSV: {exc}")

st.divider()
st.caption(
    "MarketStrength starter build | Prices supplied by Yahoo Finance where available. "
    "Data availability and ticker mappings may vary."
)
