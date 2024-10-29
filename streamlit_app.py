import streamlit as st
import pandas as pd
import plotly.express as px
import aiohttp
import asyncio
import time
from datetime import datetime

# Custom CSS for simple card border
st.markdown("""
<style>
    div[data-testid="stColumn"] {
        background-color: #ffffff;
        border: 10px solid #ffffff;
        border-radius: 10px;
        color: #000000;
        height: auto;
        margin: 0;
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'crypto_data' not in st.session_state:
    st.session_state.crypto_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

async def fetch_crypto_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': '100',
        'page': '1',
        'sparkline': 'false'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return pd.DataFrame(data)
                else:
                    st.error(f"API Error: Status code {response.status}")
                    return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def display_dashboard(df):
    # Streamlit UI
    st.title("Crypto Dashboard")
    
    # Display last update time
    if st.session_state.last_update:
        st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

    # Create container for metrics
    metrics_container = st.container()

    # 4 cards per row
    cols_per_row = 4
    for i in range(0, len(df), cols_per_row):
        cols = metrics_container.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(df):
                row = df.iloc[i + j]
                with cols[j]:
                    # Display logo first
                    if pd.notna(row["image"]):
                        st.image(row["image"], width=50)
                    
                    # Format price with appropriate decimal places
                    price = f"${row['current_price']:,.2f}"
                    
                    # Handle None values in price change
                    if pd.notna(row['price_change_percentage_24h']):
                        change = f"{row['price_change_percentage_24h']:.2f}%"
                        delta_color = "normal"
                    else:
                        change = "N/A"
                        delta_color = "normal"
                    
                    # Display metric below logo
                    st.metric(
                        label=row["name"],
                        value=price,
                        delta=change,
                        delta_color=delta_color
                    )

    # Create market cap visualization
    st.subheader("Market Cap Comparison")
    fig = px.bar(
        df.sort_values("market_cap", ascending=True).tail(20),
        x="market_cap",
        y="name",
        orientation='h',
        title="Top 20 Cryptocurrencies by Market Cap",
        labels={"market_cap": "Market Cap (USD)", "name": "Cryptocurrency"}
    )

    fig.update_layout(
        height=600,
        xaxis_title="Market Cap (USD)",
        yaxis_title="Cryptocurrency",
        showlegend=False
    )

    fig.update_xaxes(tickformat="$.2s")
    st.plotly_chart(fig, use_container_width=True)

async def main():
    # Add a refresh button
    if st.button("Refresh Data"):
        st.session_state.crypto_data = None
    
    # Fetch new data if needed
    if st.session_state.crypto_data is None:
        with st.spinner("Fetching cryptocurrency data..."):
            st.session_state.crypto_data = await fetch_crypto_data()
            st.session_state.last_update = datetime.now()
            
    # Display dashboard if we have data
    if st.session_state.crypto_data is not None:
        display_dashboard(st.session_state.crypto_data)
    
    # Schedule next update
    if st.session_state.crypto_data is not None:
        time_since_update = (datetime.now() - st.session_state.last_update).seconds
        if time_since_update >= 60:  # Update every minute
            st.session_state.crypto_data = None
            st.experimental_rerun()

# Run the app
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    asyncio.run(main())
