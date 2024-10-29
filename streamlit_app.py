import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Page config
st.set_page_config(page_title='Crypto Dashboard', page_icon=':bar_chart:')

# API call
url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false'
coins = requests.get(url).json()
df = pd.DataFrame(coins)

# Top bar
st.title('Crypto Dashboard')
st.markdown('*Top 100 coins by market cap*')

# Coin selection
selected_coin = st.selectbox('Select a coin', df['name'].unique())
selected_df = df[df['name']==selected_coin]

# Data display 
col1, col2 = st.columns(2)
col1.metric(label=selected_coin, value=f'${selected_df["current_price"].values[0]:,.2f}') 
col2.metric(label='% Change (24hr)', value=f'{selected_df["price_change_percentage_24h"].values[0]:.2f}%')

# Chart 
fig = px.line(selected_df, x='market_cap_rank', y=["market_cap", "current_price"])
st.plotly_chart(fig, use_container_width=True)
