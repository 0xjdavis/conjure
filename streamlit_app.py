import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# API call to get crypto data
url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false'
crypto_data = requests.get(url).json()

# Convert to dataframe  
df = pd.DataFrame(crypto_data)

# Display as cards
for i in range(0, len(df), 4):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.header(df.iloc[i]['name'])
        st.metric("Price", df.iloc[i]['current_price'], df.iloc[i]['price_change_percentage_24h'])
    with col2:
        st.header(df.iloc[i+1]['name'])
        st.metric("Price", df.iloc[i+1]['current_price'], df.iloc[i+1]['price_change_percentage_24h'])  
    with col3:
        st.header(df.iloc[i+2]['name'])
        st.metric("Price", df.iloc[i+2]['current_price'], df.iloc[i+2]['price_change_percentage_24h'])
    with col4:
        st.header(df.iloc[i+3]['name']) 
        st.metric("Price", df.iloc[i+3]['current_price'], df.iloc[i+3]['price_change_percentage_24h'])
