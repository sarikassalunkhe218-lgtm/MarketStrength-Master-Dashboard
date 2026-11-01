"Enter percentages as percentage points: type 15 for 15%. "
            "Debt / Equity, Current Ratio and P/E are ordinary numeric values."
        )
        edited_fundamentals = st.data_editor(
            st.session_state["fundamentals_input"],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="fundamentals_data_editor",
            column_config={
                "Symbol": st.column_config.TextColumn("NSE Symbol", required=True),
                "Company Name": st.column_config.TextColumn("Company Name"),
                "Sector": st.column_config.TextColumn("Sector"),
                "Revenue Growth YoY %": st.column_config.NumberColumn("Revenue Growth YoY %", format="%.2f"),
                "Net Profit Growth YoY %": st.column_config.NumberColumn("Net Profit Growth YoY %", format="%.2f"),
                "ROE %": st.column_config.NumberColumn("ROE %", format="%.2f"),
                "ROCE %": st.column_config.NumberColumn("ROCE %", format="%.2f"),
                "Operating Margin %": st.column_config.NumberColumn("Operating Margin %", format="%.2f"),
                "Debt / Equity": st.column_config.NumberColumn("Debt / Equity", format="%.2f"),
                "Current Ratio": st.column_config.NumberColumn("Current Ratio", format="%.2f"),
                "P/E": st.column_config.NumberColumn("P/E", format="%.2f"),
                "Financial Period": st.column_config.TextColumn("Financial Period")
            }
        )
        st.session_state["fundamentals_input"] = edited_fundamentals

        scored = calculate_fundamental_scores(edited_fundamentals)
        if not scored.empty:
            valid_scores = scored["Fundamental Score"].dropna()
            c1, c2, c3 = st.columns(3)
            c1.metric("Stocks in data", len(scored))
            c2.metric("Stocks scored", len(valid_scores))
            c3.metric("Strong fundamentals", int((scored["Scanner View"] == "STRONG FUNDAMENTALS").sum()))

            st.subheader("Fundamentals Ranking")
            display_cols = [
                "Rank", "Symbol", "Company Name", "Sector",
                "Revenue Growth YoY %", "Net Profit Growth YoY %",
                "ROE %", "ROCE %", "Operating Margin %",
                "Debt / Equity", "Current Ratio", "P/E",
                "Fundamental Score", "Scanner View"
            ]
            display_cols = [c for c in display_cols if c in scored.columns]
            st.dataframe(
                scored[display_cols],
                use_container_width=True,
                hide_index=True
            )
            st.download_button(
                "Download Fundamentals Results CSV",
                scored.to_csv(index=False).encode("utf-8"),
                "MarketStrength_Fundamentals_Results.csv",
                "text/csv"
            )
            st.caption(
                "Score weights: revenue growth 15%, profit growth 20%, ROE 15%, "
                "ROCE 20%, operating margin 10%, debt/equity 10%, current ratio 10%. "
                "At least 5 of 7 metrics are required; missing metrics are excluded "
                "and the remaining weights are normalized. P/E is displayed but not "
                "included in this quality score."
            )
        else:
            st.warning("No fundamentals data to score yet.")


# ---------- MASTER DASHBOARD ----------

else:
    st.header("MarketStrength Master Dashboard")

    st.markdown("""
    ### Analysis workflow

    1. Market Trend
    2. Sector Rotation
    3. Strong Stocks
    4. Stage Analysis
    5. Fundamentals Scanner
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
        "Run Sector Rotation, Nifty 500 Scanner and Stage Analysis "
        "from the sidebar to view the current research results."
    )

st.caption(
    "MarketStrength Master Dashboard | Research tool"
)
