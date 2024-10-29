import streamlit as st
import pandas as pd
import plotly.express as px
import aiohttp
import asyncio
from asyncio import TimeoutError
import json

# Custom CSS for simple card border
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #ffffff;
        border: 10px solid #ff0000;
        border-radius: 10px;
        margin: 0.2rem;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

async def fetch_crypto_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': '100',
        'page': '1',
        'sparkline': 'True'  # Changed to string 'false' instead of boolean False
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
    except TimeoutError:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# Create async function to run the entire app
async def run_app():
    # Fetch data asynchronously
    df = await fetch_crypto_data()
    
    if df is None:
        st.stop()
    
    # Streamlit UI
    st.title("Crypto Dashboard")

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

# Run the async app
if __name__ == "__main__":
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the async app
    loop.run_until_complete(run_app())
