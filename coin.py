import streamlit as st
import pandas as pd
import requests
import json
import hmac
import hashlib
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


BASE_URL = 'https://api.coindcx.com'
INVESTMENT_VALUE = float(st.secrets["COIN_INVESTMENT_AMOUNT"])

class CoinDCXAPI:
    def __init__(self):
        self.api_key = st.secrets["COIN_API_KEY"]
        self.api_secret = st.secrets["COIN_API_SECRET"]

    def get_balances(self):
        """Get user balances"""
        try:
            secret_bytes = bytes(self.api_secret, encoding='utf-8')
            timeStamp = int(round(time.time() * 1000))
            body = {
                "timestamp": timeStamp
            }
            json_body = json.dumps(body, separators=(',', ':'))
            signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
            headers = {
                'Content-Type': 'application/json',
                'X-AUTH-APIKEY': self.api_key,
                'X-AUTH-SIGNATURE': signature
            }

            response = requests.post(f'{BASE_URL}/exchange/v1/users/balances', data=json_body, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            st.error(f"Error fetching balances: {e}")
            return []

    def get_market_data(self):
        """Get current market data for all pairs"""
        try:
            response = requests.get('https://api.coindcx.com/exchange/ticker')
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Market data API Error: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching market data: {e}")
            return []

    def get_coin_details(self):
        """Get coin details and mappings"""
        try:
            response = requests.get('https://api.coindcx.com/exchange/v1/markets_details')
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Coin details API Error: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching coin details: {e}")
            return []

    def get_investment_amount(self):
        """Get overall investment amount"""
        value = INVESTMENT_VALUE
        return value


    def safe_float_convert(self,value):
        """Safely convert value to float, handling None and other edge cases"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


    def format_currency(self,value):
        """Format currency values"""
        try:
            value = float(value)
            if value >= 1000:
                return f"₹{value:,.2f}"
            elif value >= 1:
                return f"₹{value:.2f}"
            else:
                return f"₹{value:.6f}"
        except (ValueError, TypeError):
            return "₹0.00"

    def main(self):
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.info("🔄 Fetching your portfolio data...")
        balances = self.get_balances()
        market_data = self.get_market_data()
        coin_details = self.get_coin_details()
        loading_placeholder.empty()
        if not balances:
            st.error("Failed to fetch balance data from CoinDCX API. Please check your credentials and try again.")
            return
        if not market_data:
            st.error("Failed to fetch market data from CoinDCX API.")
            return
        # Process coin details to create mapping
        coin_mapping = {}
        if coin_details:
            for coin in coin_details:
                coin_mapping[coin['symbol']] = coin['base_currency_short_name']
        # Create market data dictionary for easy lookup with safe float conversion
        market_dict = {}
        for item in market_data:
            if item.get('last_price') is not None:
                try:
                    market_dict[item['market']] = self.safe_float_convert(item['last_price'])
                except (ValueError, TypeError) as e:
                    st.warning(f"Could not convert price for {item['market']}: {item.get('last_price')}")
                    market_dict[item['market']] = 0.0
            else:
                market_dict[item['market']] = 0.0
        # Process portfolio data
        portfolio_data = []
        total_current_value = 0

        for balance in balances:
            coin_symbol = balance['currency']
            balance_amount = self.safe_float_convert(balance['balance'])
            locked_amount = self.safe_float_convert(balance['locked_balance'])
            total_amount = balance_amount + locked_amount

            # Only process coins with positive balance
            if total_amount > 0:
                current_price = 0
                coin_name = coin_symbol
                possible_pairs = [
                    f"{coin_symbol}INR",
                    f"{coin_symbol}USDT",
                    f"{coin_symbol}BTC",
                    f"{coin_symbol}ETH",
                    f"{coin_symbol}USDC"
                ]
                for pair in possible_pairs:
                    if pair in market_dict and market_dict[pair] > 0:
                        current_price = market_dict[pair]
                        break
                # If no price found, try to find any pair containing this coin
                if current_price == 0:
                    for market_pair, price in market_dict.items():
                        if market_pair.startswith(coin_symbol) and price > 0:
                            current_price = price
                            break

                # Get coin name from mapping if available
                if coin_symbol in coin_mapping:
                    coin_name = coin_mapping[coin_symbol]

                if current_price > 0:
                    current_value = total_amount * current_price

                    portfolio_data.append({
                        'Coin': coin_name,
                        'Symbol': coin_symbol,
                        'Balance': balance_amount,
                        'Locked': locked_amount,
                        'Total Amount': total_amount,
                        'Current Price': current_price,
                        'Current Value': current_value
                    })

                    total_current_value += current_value

        if not portfolio_data:
            st.warning("No coins with valid price data found in your portfolio.")

            # Show what coins we found but couldn't price
            unpriced_coins = []
            for balance in balances:
                if self.safe_float_convert(balance['balance']) + self.safe_float_convert(balance['locked']) > 0:
                    unpriced_coins.append(balance['currency'])

            if unpriced_coins:
                st.write("Coins found but not priced:", unpriced_coins)

            return

        # Create DataFrame
        df = pd.DataFrame(portfolio_data)

        # Calculate overall investment and profit/loss
        total_investment = self.get_investment_amount()
        total_profit_loss = total_current_value - total_investment
        total_profit_loss_percent = (total_profit_loss / total_investment) * 100 if total_investment > 0 else 0

        # Display overall metrics
        st.subheader("💰 CoinDCX Portfolio Summary")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Portfolio Value",
                self.format_currency(total_current_value),
                f"{total_profit_loss_percent:.2f}%"
            )

        with col2:
            st.metric(
                "Total Investment",
                self.format_currency(total_investment)
            )

        with col3:
            st.metric(
                "Total Profit/Loss",
                self.format_currency(total_profit_loss),
                f"{total_profit_loss_percent:.2f}%"
            )

        with col4:
            st.metric(
                "Number of Coins",
                len(df)
            )


        # Create tabs for different views
        if st.button("🔄 Refresh Data"):
            st.rerun()
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write('----')
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Portfolio Allocation")
            if len(df) > 0:
                fig_pie = px.pie(
                    df,
                    values='Current Value',
                    names='Coin',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=500)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No data available for portfolio allocation chart")

        with col2:
            st.subheader("Highest Value Coins")
            if len(df) > 0:
                top_coins = df.nlargest(5, 'Current Value')[['Coin', 'Current Value']]
                for _, row in top_coins.iterrows():
                    st.metric(
                        f"{row['Coin']}",
                        self.format_currency(row['Current Value'])
                    )
            else:
                st.info("No coin data available")

        st.write('----')
        # Value distribution chart
        st.subheader("Portfolio Value Distribution")
        if len(df) > 0:
            fig_bar = px.bar(
                df.sort_values('Current Value', ascending=False),
                x='Coin',
                y='Current Value',
                color='Current Value',
                color_continuous_scale='Viridis'
            )
            fig_bar.update_layout(height=500)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No data available for value distribution chart")

        st.write('----')
        # Detailed coin information
        st.subheader("Detailed Coin Information")

        if len(df) > 0:
            # Format the dataframe for display
            display_df = df.copy()
            display_df['Current Price'] = display_df['Current Price'].apply(lambda x: f"₹{x:.6f}")
            display_df['Current Value'] = display_df['Current Value'].apply(self.format_currency)

            st.dataframe(
                display_df[[
                    'Coin', 'Symbol', 'Total Amount', 'Current Price', 'Current Value'
                ]],
                use_container_width=True
            )

            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"coindcx_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No coin data available")

        st.write('----')
        # Debug information
        st.subheader("Debug Information")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Raw Balances (first 5):**")
            st.json(balances[:5])

        with col2:
            st.write("**Portfolio Data:**")
            st.dataframe(df)

            st.write("**Market Pairs Found:**", len(market_dict))
            st.write("**Sample Market Prices:**")
            sample_prices = {k: v for i, (k, v) in enumerate(market_dict.items()) if v > 0 and i < 10}
            st.json(sample_prices)

        # Last updated timestamp and refresh
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
            st.write('')


if __name__ == "__main__":
    obj = CoinDCXAPI()
    obj.main()