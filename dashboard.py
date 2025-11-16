import streamlit as st
from zerodha import ZerodhaKiteAPI
from fixeddeposit import FixedDepositApp
import pandas as pd

st.set_page_config(page_title="Kite API Dashboard",page_icon="📈",layout="wide",initial_sidebar_state="expanded")
st.title("Financial Portfolio Dashboard 📈")
zerodhaobj = ZerodhaKiteAPI()
zerodhaobj.authenticate_kite()
fdobj = FixedDepositApp()

tab1, tab2, tab3, tab4 = st.tabs(["Total Overview", "Mutual Fund Holdings", "Coins Holdings", "FD Holdings"])

with tab1:
    st.info('Total Output Overview Coming Soon!')
with tab2:
    mf_holdings_data = zerodhaobj.get_mf_holdings()
    if not mf_holdings_data:
        st.info("No mutual fund holdings found.")
    else:
        mf_df = pd.DataFrame(mf_holdings_data)
        mf_df.columns = mf_df.columns.str.strip().str.lower()
        graph_table = mf_df[['fund', 'last_price', 'quantity', 'average_price']].copy()
        graph_table['invested_amount'] = graph_table['quantity'] * graph_table['average_price']
        graph_table['current_amount'] = graph_table['last_price'] * graph_table['quantity']
        graph_table['profit'] = graph_table['current_amount'] - graph_table['invested_amount']
        graph_table['profit%'] = (graph_table['profit'] / graph_table['invested_amount']) * 100.00
        zerodhaobj.display_mutual_fund_metrics(graph_table)
with tab3:
    st.info('Coin Holdings Overview Coming Soon!')
with tab4:
    fd_df = fdobj.dashboard()
    fdobj.dashboard_metrics(fd_df)


