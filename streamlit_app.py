import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# API call to get crypto data
url = 'https://api.coingecko.com/api/v3/coins/markets'
params = {'vs_currency':'usd', 'order':'market_cap_desc','per_page':100,'page':1,'sparkline':False} 

data = requests.get(url, params=params).json()
df = pd.DataFrame(data)

# Streamlit UI
st.title("Crypto Dashboard")
for i, row in df.iterrows():
    # Create card for each crypto
    with st.container():
        col1, col2 = st.columns(2)
        change = f"{row['price_change_percentage_24h']:.2f}%"
        color = "green" if change > 0 else "red"

        with col1: 
            st.metric(row["name"], row["current_price"], change, delta_color=color)

        with col2:
            st.image(row["image"])

fig = px.bar(df.sort_values("market_cap", ascending=False), x="market_cap", y="name")
st.plotly_chart(fig)
