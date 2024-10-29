import streamlit as st
import pandas as pd
import requests

# API call to get crypto data
url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false'
response = requests.get(url)
data = response.json()

# Dataframe to store data
df = pd.DataFrame(data)

# Streamlit UI
st.title('Crypto Dashboard')
for i in range(len(df)):
    coin_name = df.iloc[i]['name']
    symbol = df.iloc[i]['symbol']
    price = round(df.iloc[i]['current_price'],2)
    change = df.iloc[i]['price_change_percentage_24h']
    if change > 0:
        change_color = 'green'
    else: 
        change_color = 'red'

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'''
            <div style='background-color:#012443;padding:15px;border-radius:5px;'>
                <b style='color:white;'>{symbol}</b><br>
                <span style='color:white;'>{coin_name}</span><br>
                <span style='color:white;'>${price}</span>
            </div>
        ''',unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
            <div style='padding:15px;'>
                <span style='{change_color}'>{change}%</span>
            </div>
        ''',unsafe_allow_html=True)
