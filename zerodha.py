import streamlit as st
import pandas as pd
from kiteconnect import KiteConnect
import logging
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

API_KEY = st.secrets["ZERODHA_API_KEY"]
API_SECRET = st.secrets["ZERODHA_API_SECRET"]
REDIRECT_URI = "http://localhost:8501/"
logging.basicConfig(level=logging.INFO)

@st.cache_resource
def get_kite_instance():
    return KiteConnect(api_key=API_KEY)

class ZerodhaKiteAPI:
    def __init__(self):
        self.kite = get_kite_instance()

    def get_auth_token(self):
        login_url = self.kite.login_url()
        st.info("Please log in to your Zerodha account to continue.")
        st.markdown(
            f"""
                <a href="{login_url}" target="_blank" rel="noopener noreferrer" style="text-decoration:none">
                    <button style="
                        background-color:#1f77b4;
                        color:#fff;
                        padding:10px 18px;
                        border:none;
                        border-radius:6px;
                        font-weight:600;
                        cursor:pointer;
                    ">
                        Connect to Kite
                    </button>
                </a>
                """,
            unsafe_allow_html=True,
        )
        st.stop()

    def authenticate_kite(self):
        if "access_token" not in st.session_state:
            query_params = st.query_params
            if 'request_token' in query_params:
                request_token = query_params['request_token']
                try:
                    data = self.kite.generate_session(request_token, api_secret=API_SECRET)
                    st.session_state.access_token = data["access_token"]
                    st.session_state.public_token = data["public_token"]
                    self.kite.set_access_token(st.session_state.access_token)
                    st.success("Authentication successful!")
                    st.experimental_rerun()
                except Exception as e:
                    self.get_auth_token()
            else:
                self.get_auth_token()
        else:
            self.kite.set_access_token(st.session_state.access_token)

    def get_user_profile(self):
        return self.kite.profile()

    def get_mf_holdings(self):
        """Fetches mutual fund holdings from the Kite API."""
        return self.kite.mf_holdings()

    def get_portfolio_xirr(self):
        """Simple function to get overall portfolio XIRR"""
        cash_flows = []
        orders = self.kite.mf_orders()
        for order in orders:
            if order.get('status', '').upper() == 'COMPLETE':
                str_date = datetime.strftime(order['order_timestamp'], '%Y-%m-%d')
                date = datetime.strptime(str_date, '%Y-%m-%d')
                amount = float(order['amount'])
                if order['transaction_type'].upper() == 'BUY':
                    cash_flows.append((date, -amount))
                else:  # SELL
                    cash_flows.append((date, amount))
        sips = self.kite.mf_sips()
        for sip in sips:
            if sip['status'].upper() == 'ACTIVE':
                str_date = datetime.strftime(sip['created'], '%Y-%m-%d %H:%M:%S')
                date = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
                total_invested = float(sip['instalments']) * float(sip['instalment_amount'])
                cash_flows.append((date, -total_invested))
        holdings = self.kite.mf_holdings()
        current_value = sum(h['quantity'] * h['last_price'] for h in holdings)
        cash_flows.append((datetime.now(), current_value))
        if len(cash_flows) < 2:
            return 0.0
        cash_flows.sort(key=lambda x: x[0])

        start_date = cash_flows[0][0]
        def calculate_npv(rate):
            return sum(amt / ((1 + rate) ** ((date - start_date).days / 365.0))
                       for date, amt in cash_flows)
        low, high = -0.99, 10.0
        for _ in range(50):
            mid = (low + high) / 2
            if calculate_npv(mid) > 0:
                low = mid
            else:
                high = mid
        return ((low + high) / 2) * 100

    def display_mutual_fund_metrics(self,graph_table):
        # =========================================================================
        # PORTFOLIO OVERVIEW SECTION
        # =========================================================================
        st.subheader("📊 Portfolio Overview")
        total_invested = graph_table['invested_amount'].sum()
        total_current = graph_table['current_amount'].sum()
        total_profit = graph_table['profit'].sum()
        overall_profit_percentage = (total_profit / total_invested) * 100 if total_invested > 0 else 0
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Invested",f"₹{total_invested:,.2f}",help="Total amount invested across all funds")
        with col2:
            st.metric("Current Value",f"₹{total_current:,.2f}",delta=f"₹{total_profit:,.2f}",help="Current portfolio value with absolute profit/loss")
        with col3:
            st.metric("Overall Return %",f"{overall_profit_percentage:.2f}%",delta=f"{overall_profit_percentage:.2f}%",help="Overall portfolio return percentage")
        with col4:
            st.metric("Number of Funds",f"{len(graph_table)}",help="Total number of mutual funds in portfolio")

        # =========================================================================
        # PERFORMANCE HIGHLIGHTS SECTION
        # =========================================================================
        st.subheader("🏆 Performance Highlights")

        # Use columns with custom styling
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            best_fund = graph_table.loc[graph_table['profit%'].idxmax()]
            st.markdown(f"""
            <div style="font-size: 14px;">
                <strong>Best Performer</strong><br>
                <span style="font-size: 12px;">{best_fund['fund']}</span><br>
                <span style="font-size: 12px; color: green;">+{best_fund['profit%']:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            worst_fund = graph_table.loc[graph_table['profit%'].idxmin()]
            st.markdown(f"""
            <div style="font-size: 14px;">
                <strong>Worst Performer</strong><br>
                <span style="font-size: 12px;">{worst_fund['fund']}</span><br>
                <span style="font-size: 12px; color: red;">{worst_fund['profit%']:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            largest_holding = graph_table.loc[graph_table['current_amount'].idxmax()]
            st.markdown(f"""
            <div style="font-size: 14px;">
                <strong>Largest Holding</strong><br>
                <span style="font-size: 12px;">{largest_holding['fund']}</span><br>
                <span style="font-size: 10px; color: green;">₹{largest_holding['current_amount']:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            highest_profit = graph_table.loc[graph_table['profit'].idxmax()]
            st.markdown(f"""
            <div style="font-size: 14px;">
                <strong>Highest Profit</strong><br>
                <span style="font-size: 12px;">{highest_profit['fund']}</span><br>
                <span style="font-size: 12px; color: green;">₹{highest_profit['profit']:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)

        # =========================================================================
        # PORTFOLIO ALLOCATION SECTION
        # =========================================================================
        st.markdown("---")
        st.subheader("📈 Portfolio Allocation")
        col1, col2 = st.columns(2)
        with col1:
            fig_allocation = px.pie(
                graph_table,
                values='current_amount',
                names='fund',
                title='Portfolio Allocation by Current Value',
                hover_data=['profit%'],
                labels={'profit%': 'Return %'}
            )
            fig_allocation.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_allocation, use_container_width=True)

        with col2:
            # Allocation by invested amount
            fig_invested = px.pie(
                graph_table,
                values='invested_amount',
                names='fund',
                title='Portfolio Allocation by Invested Amount',
                color='profit%'
            )
            fig_invested.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_invested, use_container_width=True)

        # =========================================================================
        # PERFORMANCE ANALYSIS SECTION
        # =========================================================================
        st.markdown("---")
        st.subheader("📊 Performance Analysis")
        col1, col2 = st.columns(2)
        with col1:
            graph_table_sorted = graph_table.sort_values('profit%', ascending=True)
            fig_returns = px.bar(
                graph_table_sorted,
                y='fund',
                x='profit%',
                title='Returns by Fund (%)',
                color='profit%',
                color_continuous_scale='RdYlGn',
                orientation='h'
            )
            fig_returns.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_returns, use_container_width=True)

        with col2:
            fig_scatter = px.scatter(
                graph_table,
                x='invested_amount',
                y='current_amount',
                color='profit%',
                hover_name='fund',
                title='Invested vs Current Value (Size = Return %)',
                color_continuous_scale='RdYlGn',
                size_max=60
            )

            max_val = max(graph_table['invested_amount'].max(), graph_table['current_amount'].max())
            fig_scatter.add_trace(
                go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    line=dict(dash='dash', color='gray'),
                    name='Break-even Line'
                )
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # =========================================================================
        # ABSOLUTE RETURNS SECTION
        # =========================================================================
        st.markdown("---")
        st.subheader("💰 Absolute Returns Analysis")

        col1, col2 = st.columns(2)
        with col1:
            # Absolute profit/loss by fund
            graph_table_abs = graph_table.sort_values('profit', ascending=True)

            fig_absolute = px.bar(
                graph_table_abs,
                x='profit',
                y='fund',
                title='Absolute Profit/Loss by Fund (₹)',
                color='profit',
                color_continuous_scale='RdYlGn',
                orientation='h'
            )
            fig_absolute.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_absolute, use_container_width=True)

        with col2:
            graph_table_melted = graph_table.copy()
            graph_table_melted['Profit/Loss'] = graph_table_melted['profit']
            graph_table_melted['Invested Amount'] = graph_table_melted['invested_amount']
            fig_stacked = go.Figure()
            fig_stacked.add_trace(go.Bar(
                y=graph_table_melted['fund'],
                x=graph_table_melted['Invested Amount'],
                name='Invested Amount',
                orientation='h',
                marker_color='lightblue'
            ))
            fig_stacked.add_trace(go.Bar(
                y=graph_table_melted['fund'],
                x=graph_table_melted['Profit/Loss'],
                name='Profit/Loss',
                orientation='h',
                marker_color=graph_table_melted['profit'].apply(
                    lambda x: 'green' if x >= 0 else 'red'
                )
            ))

            fig_stacked.update_layout(
                title='Invested Amount vs Profit/Loss',
                barmode='stack',
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig_stacked, use_container_width=True)

        # =========================================================================
        # INDIVIDUAL FUND ANALYSIS SECTION
        # =========================================================================
        st.markdown("---")
        st.subheader("🔍 Individual Fund Analysis")
        selected_fund = st.selectbox(
            "Select a fund to view detailed analysis:",
            graph_table['fund'].unique()
        )

        if selected_fund:
            fund_data = graph_table[graph_table['fund'] == selected_fund].iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Quantity", f"{fund_data['quantity']:,.2f}")
            with col2:
                st.metric("Average Price", f"₹{fund_data['average_price']:,.2f}")
            with col3:
                st.metric("Current Price", f"₹{fund_data['last_price']:,.2f}")
            with col4:
                st.metric("Return %", f"{fund_data['profit%']:.2f}%")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Invested Amount", f"₹{fund_data['invested_amount']:,.2f}")
            with col2:
                st.metric("Current Value", f"₹{fund_data['current_amount']:,.2f}")
            with col3:
                st.metric("Absolute Profit", f"₹{fund_data['profit']:,.2f}")
            with col4:
                portfolio_weight = (fund_data['current_amount'] / total_current) * 100
                st.metric("Portfolio Weight", f"{portfolio_weight:.2f}%")

            return_pct = fund_data['profit%']
            max_pct = max(abs(return_pct), 20)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=return_pct,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"Return Percentage for {selected_fund}"},
                delta={'reference': 0},
                gauge={
                    'axis': {'range': [-max_pct, max_pct]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [-max_pct, 0], 'color': "lightcoral"},
                        {'range': [0, max_pct], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': return_pct
                    }
                }
            ))

            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)

        # =========================================================================
        # DETAILED TABLE SECTION
        # =========================================================================
        st.markdown("---")
        st.subheader("📋 Detailed Portfolio Table")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_return = graph_table['profit%'].mean()
            st.metric("Average Return %", f"{avg_return:.2f}%")
        with col2:
            median_return = graph_table['profit%'].median()
            st.metric("Median Return %", f"{median_return:.2f}%")
        with col3:
            positive_funds = len(graph_table[graph_table['profit%'] > 0])
            st.metric("Profitable Funds", f"{positive_funds}/{len(graph_table)}")
        with col4:
            max_drawdown = graph_table['profit%'].min()
            st.metric("Maximum Drawdown", f"{max_drawdown:.2f}%")

        display_table = graph_table.copy()
        display_table = display_table.sort_values('current_amount', ascending=False)
        display_table_formatted = display_table.copy()
        display_table_formatted['invested_amount'] = display_table_formatted['invested_amount'].apply(lambda x: f"₹{x:,.2f}")
        display_table_formatted['current_amount'] = display_table_formatted['current_amount'].apply(lambda x: f"₹{x:,.2f}")
        display_table_formatted['profit'] = display_table_formatted['profit'].apply(lambda x: f"₹{x:,.2f}")
        display_table_formatted['profit%'] = display_table_formatted['profit%'].apply(lambda x: f"{x:.2f}%")
        display_table_formatted['average_price'] = display_table_formatted['average_price'].apply(lambda x: f"₹{x:,.2f}")
        display_table_formatted['last_price'] = display_table_formatted['last_price'].apply(lambda x: f"₹{x:,.2f}")
        display_table_formatted['quantity'] = display_table_formatted['quantity'].apply(lambda x: f"{x:,.2f}")
        st.dataframe(display_table_formatted, use_container_width=True)
        st.markdown("---")
