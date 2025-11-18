import streamlit as st
import pandas as pd
import altair as alt

class OverallMetrics:
    def investment_dashboard(self,mutual_funds_df: pd.DataFrame, fd_df: pd.DataFrame):
        # -------------------------------------------------------------
        # 🔹 MUTUAL FUND METRICS
        # -------------------------------------------------------------
        mf_invested = mutual_funds_df["invested_amount"].sum()
        mf_current = mutual_funds_df["current_amount"].sum()
        mf_profit = mf_current - mf_invested
        mf_profit_percent = (mf_profit / mf_invested * 100) if mf_invested else 0

        # -------------------------------------------------------------
        # 🔹 FD METRICS
        # -------------------------------------------------------------
        fd_invested = fd_df["FD Value"].sum()
        fd_current = fd_df["Total Value"].sum()
        fd_profit = fd_current - fd_invested
        fd_profit_percent = (fd_profit / fd_invested * 100) if fd_invested else 0

        # -------------------------------------------------------------
        # 🔹 OVERALL METRICS
        # -------------------------------------------------------------
        total_invested = mf_invested + fd_invested
        total_current = mf_current + fd_current
        total_profit = total_current - total_invested
        total_profit_percent = (total_profit / total_invested * 100) if total_invested else 0

        # =====================================================================
        # 📌 TOP SUMMARY SECTION
        # =====================================================================
        st.subheader("📌 Overall Portfolio Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Invested", f"₹{total_invested:,.2f}")
        c2.metric("Current Value", f"₹{total_current:,.2f}")
        c3.metric("Total Profit", f"₹{total_profit:,.2f}")
        c4.metric("Profit %", f"{total_profit_percent:.2f}%")

        # =====================================================================
        # 🏦 ASSET CLASS CONTRIBUTION
        # =====================================================================
        st.subheader("🏦 Asset Class Contribution")
        asset_df = pd.DataFrame({
            "Asset Class": ["Mutual Funds", "Fixed Deposits"],
            "Invested": [mf_invested, fd_invested],
            "Current": [mf_current, fd_current]
        })

        st.bar_chart(asset_df.set_index("Asset Class"))

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("MF Invested %", f"{(mf_invested / total_invested * 100):.2f}%")
        d2.metric("FD Invested %", f"{(fd_invested / total_invested * 100):.2f}%")
        d3.metric("MF Current %", f"{(mf_current / total_current * 100):.2f}%")
        d4.metric("FD Current %", f"{(fd_current / total_current * 100):.2f}%")

        # Pie chart
        st.subheader("📌 Asset Allocation (Current Value)")
        pie_df = pd.DataFrame({
            "Asset Class": ["Mutual Funds", "Fixed Deposits"],
            "Value": [mf_current, fd_current]
        })

        chart = alt.Chart(pie_df).mark_arc().encode(
            theta="Value",
            color="Asset Class",
            tooltip=["Asset Class", "Value"]
        )
        st.altair_chart(chart, use_container_width=True)

        # =====================================================================
        # 📘 MUTUAL FUNDS SECTION
        # =====================================================================
        st.subheader("📘 Mutual Fund Summary")

        b1, b2, b3 = st.columns(3)
        b1.metric("MF Invested", f"₹{mf_invested:,.2f}")
        b2.metric("MF Current", f"₹{mf_current:,.2f}")
        b3.metric("MF Profit %", f"{mf_profit_percent:.2f}%")

        # Best / Worst performers
        best = mutual_funds_df.loc[mutual_funds_df["profit%"].idxmax()]
        worst = mutual_funds_df.loc[mutual_funds_df["profit%"].idxmin()]

        st.write(f"**Best Performing Fund:** {best['fund']} ({best['profit%']:.2f}%)")
        st.write(f"**Worst Performing Fund:** {worst['fund']} ({worst['profit%']:.2f}%)")

        # Charts
        st.subheader("💼 Fund-wise Current Value")
        st.bar_chart(mutual_funds_df.set_index("fund")["current_amount"])

        st.subheader("📈 Mutual Fund Performance (%)")
        st.bar_chart(mutual_funds_df.set_index("fund")["profit%"])

        st.subheader("📒 Mutual Fund Table")
        st.dataframe(mutual_funds_df, use_container_width=True)

        # =====================================================================
        # 💰 FIXED DEPOSITS SECTION
        # =====================================================================
        st.subheader("💰 Fixed Deposit Summary")

        fd_cols = st.columns(3)
        fd_cols[0].metric("FD Invested", f"₹{fd_invested:,.2f}")
        fd_cols[1].metric("FD Current", f"₹{fd_current:,.2f}")
        fd_cols[2].metric("FD Profit %", f"{fd_profit_percent:.2f}%")

        avg_fd_rate = fd_df["Interest Rate"].mean()
        total_fd_interest_earned = fd_df["Interest"].sum()
        weighted_fd_yield = (total_fd_interest_earned / fd_invested * 100) if fd_invested else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg FD Interest Rate", f"{avg_fd_rate:.2f}%")
        c2.metric("Total FD Interest Earned", f"₹{total_fd_interest_earned:,.2f}")
        c3.metric("Weighted FD Yield", f"{weighted_fd_yield:.2f}%")

        # Upcoming maturities
        st.subheader("⏳ Upcoming FD Maturities")
        fd_30 = fd_df[fd_df["Days of Maturity Left"] <= 30]["Total Value"].sum()
        fd_90 = fd_df[fd_df["Days of Maturity Left"] <= 90]["Total Value"].sum()

        m1, m2 = st.columns(2)
        m1.metric("Maturing in 30 Days", f"₹{fd_30:,.2f}")
        m2.metric("Maturing in 90 Days", f"₹{fd_90:,.2f}")

        st.subheader("🕒 FD Maturity Timeline")
        st.bar_chart(fd_df.set_index("FD Name")["Days of Maturity Left"])

        st.subheader("📒 Fixed Deposit Table")
        st.dataframe(fd_df, use_container_width=True)

        # =====================================================================
        # 📊 PORTFOLIO CHARTS SECTION
        # =====================================================================
        st.subheader("📊 Additional Portfolio Charts")

        st.write("### 💸 Profit Contribution by Fund")
        st.bar_chart(mutual_funds_df.set_index("fund")["profit"])

        st.write("### 🏦 FD Exposure by Bank")
        st.bar_chart(fd_df.set_index("Bank")["FD Value"])

        combined = pd.DataFrame({
            "Mutual Funds": [mf_current],
            "Fixed Deposits": [fd_current]
        })
        st.write("### 📊 Current Value by Asset Class")
        st.bar_chart(combined.T)

