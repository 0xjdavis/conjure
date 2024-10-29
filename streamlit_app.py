import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
import time
from datetime import datetime, timedelta

# st.set_page_config(layout="wide")

# Custom CSS for simple card border
st.markdown("""
<style>
    div[data-testid="stColumn"] {
        align-items: center;
        background-color: #ffffff;
        border: 10px solid #ffffff;
        border-radius: 10px;
        color: #000000;
        display: flex;
        justify-content: center;
        height: auto;
        margin: 0;
        max-width:150px
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'crypto_data' not in st.session_state:
    st.session_state.crypto_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None


async def fetch_historical_prices(session, coin_id):
    days = '30'
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily'
    }
    
    try:
        async with session.get(url, params=params, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                prices['timestamp'] = pd.to_datetime(prices['timestamp'], unit='ms')
                return prices
            return None
    except Exception:
        return None

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
            # Fetch current market data
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    df = pd.DataFrame(data)
                    
                    # Fetch historical data for each coin
                    historical_data = {}
                    for coin in data:
                        hist_prices = await fetch_historical_prices(session, coin['id'])
                        if hist_prices is not None:
                            historical_data[coin['id']] = hist_prices
                    
                    return df, historical_data
                else:
                    st.error(f"API Error: Status code {response.status}")
                    return None, None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None, None

def create_sparkline(prices_df, current_price):
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=prices_df['timestamp'],
        y=prices_df['price'],
        line=dict(color='blue', width=1),
        showlegend=False
    ))
    
    # Update layout for minimal appearance
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        )
    )
    
    return fig

def display_dashboard(df, historical_data, placeholder):
    with placeholder.container():
        # Streamlit UI
        st.title("Crypto Dashboard")
        
        # Display last update time
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
                        
                        # Add sparkline chart if historical data is available
                        if row['id'] in historical_data:
                            fig = create_sparkline(
                                historical_data[row['id']], 
                                row['current_price']
                            )
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

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
    # Create a placeholder for the entire dashboard
    dashboard_placeholder = st.empty()
    
    while True:
        # Fetch new data
        df, historical_data = await fetch_crypto_data()
        
        if df is not None and historical_data is not None:
            # Update the dashboard with new data
            display_dashboard(df, historical_data, dashboard_placeholder)
        
        # Wait for 60 seconds before next update
        await asyncio.sleep(60)

# Run the async app
if __name__ == "__main__":
    asyncio.run(main())
