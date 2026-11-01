
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption("India + Global | Stocks + ETFs")

st.warning(
    "Data status: Demo until you import verified market data. "
    "No live prices or automated trading signals are provided yet."
)

PAGES = [
    "Master Dashboard",
    "Sector Rotation (RRG)",
    "Stage Analysis",
    "Relative Strength",
    "Momentum Scanner",
    "VCP Scanner",
    "Chart Patterns",
    "Breakout / Breakdown",
    "Trend Reversal",
    "Fundamentals",
    "Bear-Market Value Scanner",
    "Stocks & ETFs Screener",
    "Watchlist",
    "Import Data"
]

page = st.sidebar.radio("Choose a module", PAGES)

st.sidebar.markdown("---")
st.sidebar.caption("MarketStrength · Version 2 starter")

if "market_data" not in st.session_state:
    st.session_state.market_data = pd.DataFrame(
        columns=[
            "Symbol", "Market", "Type", "Sector",
            "RS_1M", "RS_3M", "RS_6M", "RS_12M",
            "Stage", "Setup", "ROE", "ROCE", "PE",
            "Debt_Equity", "Signal"
        ]
    )

data = st.session_state.market_data

def show_data():
    if data.empty:
        st.info("No market data loaded. Open Import Data to upload a CSV file.")
    else:
        st.dataframe(data, use_container_width=True, hide_index=True)

if page == "Master Dashboard":
    st.subheader("Market Overview")
    a, b, c, d = st.columns(4)
    a.metric("Markets", "India + Global")
    b.metric("Asset classes", "Stocks + ETFs")
    c.metric("Loaded instruments", len(data))
    d.metric("Data status", "Not loaded" if data.empty else "CSV imported")

    st.subheader("Research workflow")
    st.write(
        "Market Trend → Strong Sectors → Strong Stocks → "
        "Stage Analysis → Momentum → Patterns → "
        "Fundamentals → Entry Review"
    )
    st.subheader("Current opportunity list")
    show_data()

elif page == "Sector Rotation (RRG)":
    st.subheader("Sector Rotation — RRG")
    st.write("Quadrants: Leading, Weakening, Improving and Lagging.")
    st.info(
        "Real RRG positioning requires historical sector prices "
        "and a benchmark series. No quadrant is calculated until "
        "those data are available."
    )
    show_data()

elif page == "Stage Analysis":
    st.subheader("Stage Analysis")
    st.write(
        "Stage 1 — Base | Stage 2 — Advancing | "
        "Stage 3 — Topping | Stage 4 — Declining"
    )
    st.info(
        "Accurate stage classification requires historical weekly "
        "prices and moving-average calculations."
    )
    show_data()

elif page == "Relative Strength":
    st.subheader("Relative Strength Scanner")
    st.write("Compare relative strength over 1M, 3M, 6M and 12M.")
    show_data()

elif page == "Momentum Scanner":
    st.subheader("Momentum Scanner")
    st.write("Planned filters: RS acceleration, trend and 52-week-high proximity.")
    show_data()

elif page == "VCP Scanner":
    st.subheader("VCP Scanner")
    st.write("Planned checks: contractions, tightening, volume dry-up and pivot.")
    st.info("VCP detection requires daily price and volume history.")
    show_data()

elif page == "Chart Patterns":
    st.subheader("Bullish and Bearish Chart Patterns")
    st.write(
        "Bullish: VCP, Cup & Handle, Double Bottom, Bull Flag, "
        "Ascending Triangle and Flat Base."
    )
    st.write(
        "Bearish: Head & Shoulders, Double Top, Bear Flag, "
        "Descending Triangle and Rising Wedge."
    )
    show_data()

elif page == "Breakout / Breakdown":
    st.subheader("Breakout / Breakdown Scanner")
    st.write("Planned checks: 20-day and 50-day levels, volume and trend.")
    show_data()

elif page == "Trend Reversal":
    st.subheader("Trend Reversal Scanner")
    st.write("Planned checks: Stage transitions, MACD, RSI and moving averages.")
    show_data()

elif page == "Fundamentals":
    st.subheader("Fundamental Analysis")
    st.write(
        "Review ROE, ROCE, PE, sales growth, profit growth, "
        "operating margins, debt and cash flow."
    )
    st.warning("Missing fundamental values must remain blank, not be guessed.")
    show_data()

elif page == "Bear-Market Value Scanner":
    st.subheader("Bear-Market Value Buying Scanner")
    st.write(
        "Purpose: find quality companies at potentially attractive "
        "valuations during market weakness."
    )
    st.markdown("""
    **Suggested configurable research filters**
    - ROE and ROCE above 15%
    - Debt/equity below 0.5
    - Positive operating cash flow
    - 5-year sales and profit growth above 10%
    - Valuation below the company's own historical average
    - Check valuation against sector peers
    - Review price stabilisation and relative strength
    """)
    st.info(
        "Stage 1 accumulation can qualify for a value watch. "
        "A price decline alone does not make a stock cheap. "
        "These filters are not calculated unless the necessary data are loaded."
    )
    show_data()

elif page == "Stocks & ETFs Screener":
    st.subheader("Stocks and ETFs Screener")
    market = st.selectbox(
        "Market",
        ["All", "India", "Global"]
    )
    kind = st.selectbox(
        "Instrument type",
        ["All", "Stock", "ETF"]
    )
    filtered = data.copy()
    if not filtered.empty:
        if market != "All":
            filtered = filtered[filtered["Market"].str.lower() == market.lower()]
        if kind != "All":
            filtered = filtered[filtered["Type"].str.lower() == kind.lower()]
    st.dataframe(filtered, use_container_width=True, hide_index=True)

elif page == "Watchlist":
    st.subheader("Watchlist")
    show_data()
    st.caption("Use your own review rules and risk limits.")

elif page == "Import Data":
    st.subheader("Import Your Market Data")
    st.write("Upload a CSV containing your verified market or screening data.")
    st.code(
        "Symbol,Market,Type,Sector,RS_1M,RS_3M,RS_6M,RS_12M,"
        "Stage,Setup,ROE,ROCE,PE,Debt_Equity,Signal",
        language="text"
    )
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_csv(uploaded)
            if "Symbol" not in incoming.columns:
                st.error("Your CSV must contain a Symbol column.")
            else:
                st.session_state.market_data = incoming
                st.success(f"Imported {len(incoming)} rows for this session.")
                st.dataframe(incoming, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Could not read the CSV: {exc}")

st.divider()
st.caption(
    "Last page opened: " + datetime.now().strftime("%d %b %Y, %H:%M")
)
st.caption(
    "Research tool only. Verify data quality, valuation and risk. "
    "Not investment advice."
)

