import streamlit as st
import pandas as pd
from cryptography.fernet import Fernet
from io import StringIO
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

@st.cache_data
def load_encrypted_data(encryption_key):
    key = encryption_key.encode()
    cipher_suite = Fernet(key)
    with open('encrypted_file.enc', 'rb') as f:
        encrypted_data = f.read()
    decrypted_bytes = cipher_suite.decrypt(encrypted_data)
    text = decrypted_bytes.decode('utf-8', errors='replace')
    text = text.replace('\ufffd', '').replace('\\xe2\\x82\\xb', '').replace('\u20b9', '').strip()
    df = pd.read_csv(StringIO(text))
    return df

class FixedDepositApp:
    def dashboard(self):
        encryption_key_token = st.secrets["encryption_key"]
        df = load_encrypted_data(encryption_key_token)
        if not df.empty:
            df['FD Start Date'] = pd.to_datetime(df['FD Start Date'], errors='coerce')
            df['FD Maturity Date'] = pd.to_datetime(df['FD Maturity Date'], errors='coerce')
            df.drop(columns = ['Unnamed: 0', '#','Days of Maturity Left'], inplace=True, errors='ignore')
            df['Days of Maturity Left'] = (df['FD Maturity Date'] - pd.to_datetime('today')).dt.days
            df['FD Value'] = pd.to_numeric(df['FD Value'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
            df['Interest Rate'] = pd.to_numeric(df['Interest Rate'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
            df['Interest'] = pd.to_numeric(df['Interest'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
            df['Total Value'] = pd.to_numeric(df['Total Value'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
            df = df.fillna(0)
            return df

    def dashboard_metrics(self, df):
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            banks = ['All'] + list(df['Bank'].unique())
            selected_bank = st.selectbox("Select Bank", banks)
        with filter_col2:
            fd_types = ['All'] + list(df['FD Name'].unique())
            selected_fd_type = st.selectbox("Select FD Number", fd_types)
            filtered_df = df.copy()
            if selected_bank != 'All':
                filtered_df = filtered_df[filtered_df['Bank'] == selected_bank]
            if selected_fd_type != 'All':
                filtered_df = filtered_df[filtered_df['FD Name'] == selected_fd_type]

        # Key Metrics
        st.header("📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_investment = filtered_df['FD Value'].sum()
            if pd.isna(total_investment):
                total_investment = 0
            st.metric("Total Investment", f"₹{float(total_investment):,.0f}")

        with col2:
            total_interest = filtered_df['Interest'].sum()
            if pd.isna(total_interest):
                total_interest = 0
            st.metric("Total Interest", f"₹{float(total_interest):,.0f}")

        with col3:
            total_value = filtered_df['Total Value'].sum()
            if pd.isna(total_value):
                total_value = 0
            st.metric("Total Maturity Value", f"₹{float(total_value):,.0f}")

        with col4:
            avg_interest_rate = filtered_df['Interest Rate'].mean()
            if pd.isna(avg_interest_rate):
                avg_interest_rate = 0
            st.metric("Avg Interest Rate", f"{float(avg_interest_rate):.2f}%")

        # Additional metrics
        col5, col6, col7, col8 = st.columns(4)

        with col5:
            active_fds = len(filtered_df)
            st.metric("Active FDs", active_fds)

        with col6:
            avg_days_to_maturity = filtered_df['Days of Maturity Left'].mean()
            if pd.isna(avg_days_to_maturity):
                avg_days_to_maturity = 0
            st.metric("Avg Days to Maturity", f"{float(avg_days_to_maturity):.0f} days")

        with col7:
            nearest_maturity = filtered_df['Days of Maturity Left'].min()
            if pd.isna(nearest_maturity):
                nearest_maturity = 0
                nearest_desc = 'N/A'
            else:
                idx = filtered_df['Days of Maturity Left'].idxmin()
                nearest_row = filtered_df.loc[idx]
                nearest_fd = nearest_row.get('FD Name', nearest_row.get('FD', 'N/A'))
                nearest_desc = f"{nearest_fd}"
            # st.metric("Nearest Maturity (Days)", f"{float(nearest_maturity):.0f}\n{nearest_desc}", nearest_desc, delta_color="off")
            st.metric("Nearest Maturity (Days)", f"{float(nearest_maturity):.0f} days", nearest_desc, delta_color="off")

        with col8:
            if not filtered_df.empty and 'Interest Rate' in filtered_df.columns:
                highest_interest_rate = filtered_df['Interest Rate'].max()
                highest_interest_bank = filtered_df.loc[filtered_df['Interest Rate'].idxmax(), 'FD Name']
                st.metric("Highest Interest Rate", f"{float(highest_interest_rate):.2f}%", highest_interest_bank)
            else:
                st.metric("Highest Interest Rate", "0%", "N/A")

        st.header("📈 Visualizations")
        col1, col2 = st.columns(2)
        with col1:
            if not filtered_df.empty:
                bank_investment = filtered_df.groupby('Bank')['FD Value'].sum().reset_index()
                fig_bank = px.pie(bank_investment, values='FD Value', names='Bank', title='Investment Distribution by Bank')
                st.plotly_chart(fig_bank, use_container_width=True)
        with col2:
            if not filtered_df.empty:
                fd_type_investment = filtered_df.groupby('FD Name')['FD Value'].sum().reset_index()
                fig_type = px.pie(fd_type_investment, values='FD Value', names='FD Name', title='Investment Distribution by FD Number')
                st.plotly_chart(fig_type, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            # Interest Rates by Bank
            if not filtered_df.empty:
                fig_interest = px.bar(filtered_df, x='Bank', y='Interest Rate', color='FD Name', title='Interest Rates by Bank and FD Type')
                st.plotly_chart(fig_interest, use_container_width=True)

        with col4:
            # Maturity Timeline
            if not filtered_df.empty:
                fig_timeline = px.scatter(filtered_df, x='FD Maturity Date', y='Total Value', size='FD Value', color='Bank', hover_name='FD Name', title='FD Maturity Timeline (Size represents FD Value)')
                st.plotly_chart(fig_timeline, use_container_width=True)

        # Row 3: Detailed Analysis
        col5, col6 = st.columns(2)

        with col5:
            # Days to Maturity Distribution
            if not filtered_df.empty:
                fig_maturity = px.histogram(filtered_df, x='Days of Maturity Left',
                                            title='Distribution of Days to Maturity')
                st.plotly_chart(fig_maturity, use_container_width=True)

        with col6:
            # Interest vs Principal
            if not filtered_df.empty:
                fig_scatter = px.scatter(filtered_df, x='FD Value', y='Interest',
                                         color='Bank', size='Interest Rate',
                                         hover_name='FD Name',
                                         title='Interest vs Principal Amount')
                st.plotly_chart(fig_scatter, use_container_width=True)

            # FD Details Table
        st.header("📋 FD Details")
        if not filtered_df.empty:
            styled_df = filtered_df.style.format({
                'FD Value': '₹{:,.0f}',
                'Interest Rate': '{:.2f}%',
                'Interest': '₹{:,.0f}',
                'Total Value': '₹{:,.0f}',
                'FD Start Date': lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '',
                'FD Maturity Date': lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
            })
            styled_df = df.rename(columns={'Total Value': 'Maturity Value'})
            st.dataframe(styled_df, use_container_width=True)

        # Summary by Nominee
        st.header("👥 Summary by Nominee")
        if 'Nominee' in filtered_df.columns and not filtered_df.empty:
            nominee_summary = filtered_df.groupby('Nominee').agg({
                'FD Value': 'sum',
                'Interest': 'sum',
                'Total Value': 'sum',
                'Bank': 'count'
            }).rename(columns={'Bank': 'Number of FDs'}).round(0)

            st.dataframe(nominee_summary.style.format({
                'FD Value': '₹{:,.0f}',
                'Interest': '₹{:,.0f}',
                'Total Value': '₹{:,.0f}'
            }), use_container_width=True)

        # Download option at the bottom
        st.header("💾 Export Data")
        if st.button("Download Filtered Data as CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Click to Download",
                data=csv,
                file_name="filtered_fd_data.csv",
                mime="text/csv"
            )


