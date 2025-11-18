import streamlit as st
from zerodha import ZerodhaKiteAPI
from fixeddeposit import FixedDepositApp
from coin import CoinDCXAPI
from overall_metrics import OverallMetrics
import pandas as pd

st.set_page_config(page_title="Kite API Dashboard",page_icon="📈",layout="wide",initial_sidebar_state="expanded")
st.title("Financial Portfolio Dashboard 📈")
zerodhaobj = ZerodhaKiteAPI()
zerodhaobj.authenticate_kite()
fdobj = FixedDepositApp()
coinobj = CoinDCXAPI()
overallmetricsobj = OverallMetrics()

tab1, tab2, tab3, tab4 = st.tabs(["Total Overview", "Mutual Fund Holdings", "Coins Holdings", "FD Holdings"])

with tab1:
    mf_holdings_data = zerodhaobj.get_mf_holdings()
    if not mf_holdings_data:
        st.info("No mutual fund holdings found.")
    else:
        mf_df = pd.DataFrame(mf_holdings_data)
        mf_df.columns = mf_df.columns.str.strip().str.lower()
        zerodha_df = mf_df[['fund', 'last_price', 'quantity', 'average_price']].copy()
        zerodha_df['invested_amount'] = zerodha_df['quantity'] * zerodha_df['average_price']
        zerodha_df['current_amount'] = zerodha_df['last_price'] * zerodha_df['quantity']
        zerodha_df['profit'] = zerodha_df['current_amount'] - zerodha_df['invested_amount']
        zerodha_df['profit%'] = (zerodha_df['profit'] / zerodha_df['invested_amount']) * 100.00
        fixeddeposit_df = fdobj.dashboard()
        overallmetricsobj.investment_dashboard(zerodha_df, fixeddeposit_df)

with tab2:
    mf_holdings_data = zerodhaobj.get_mf_holdings()
    if not mf_holdings_data:
        st.info("No mutual fund holdings found.")
    else:
        mf_df = pd.DataFrame(mf_holdings_data)
        mf_df.columns = mf_df.columns.str.strip().str.lower()
        graph_table = mf_df[['fund', 'last_price', 'quantity', 'average_price', 'folio']].copy()
        graph_table['invested_amount'] = graph_table['quantity'] * graph_table['average_price']
        graph_table['current_amount'] = graph_table['last_price'] * graph_table['quantity']
        graph_table['profit'] = graph_table['current_amount'] - graph_table['invested_amount']
        graph_table['profit%'] = (graph_table['profit'] / graph_table['invested_amount']) * 100.00
        zerodhaobj.display_mutual_fund_metrics(graph_table)
with tab3:
    coinobj.main()
with tab4:
    fd_df = fdobj.dashboard()
    fdobj.dashboard_metrics(fd_df)
