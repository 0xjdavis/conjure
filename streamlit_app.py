import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Page config
st.set_page_config(page_title='Crypto Dashboard', page_icon=':chart_with_upwards_trend:')

# API requests
url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false'
coins = requests.get(url).json()
df = pd.DataFrame(coins)

# Top bar
st.header('Top 100 Cryptocurrencies by Market Cap')

# Coin cards
for i in range(0,100,5):
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    for j in range(5):
        with columns[j]:
            name = df.iloc[i+j]['name']
            symbol = df.iloc[i+j]['symbol']
            price = round(df.iloc[i+j]['current_price'],2)
            market_cap = int(df.iloc[i+j]['market_cap'])
            market_cap_str = f'{market_cap:,}'
            logo = df.iloc[i+j]['image']
            change_24 = round(df.iloc[i+j]['price_change_percentage_24h'],2)

            st.image(logo,width=50)
            st.write(f'#{i+j+1}')
            st.write(f'**{name}**')
            st.write(f'{symbol}')
            st.write(f'${price}')
            st.write(f'Market Cap: ${market_cap_str}')
            st.write(f'{change_24}%')

# Market metrics
st.header('Market Metrics')
total_cap = int(df['market_cap'].sum())
st.metric(label="Total Market Cap", value=f'${total_cap:,}')

# Chart 
chart = px.line(df.head(10), y="current_price", title='Top 10 Cryptocurrencies by Market Cap')
st.plotly_chart(chart)
