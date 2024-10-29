import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime

st.set_page_config(layout="wide")

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
        'sparkline': 'true',  # Changed to true to get sparkline data directly
        'price_change_percentage': '30d'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    df = pd.DataFrame(data)
                    return df
                else:
                    st.error(f"API Error: Status code {response.status}")
                    return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def create_sparkline(sparkline_data):
    fig = go.Figure()
    
    # Create x-axis points (7 days worth of data)
    x_points = list(range(len(sparkline_data)))
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=x_points,
        y=sparkline_data,
        line=dict(color='rgb(49, 130, 189)', width=1),
        showlegend=False
    ))
    
    # Update layout for minimal appearance
    fig.update_layout(
        height=50,  # Reduced height
        width=150,  # Fixed width
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=True
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=True
        )
    )
    
    return fig

def display_dashboard(df, placeholder):
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
                        
                        # Create sparkline from the sparkline data
                        if pd.notna(row['sparkline_in_7d']) and row['sparkline_in_7d'].get('price'):
                            fig = create_sparkline(row['sparkline_in_7d']['price'])
                            st.plotly_chart(
                                fig, 
                                use_container_width=False,  # Changed to False
                                config={
                                    'displayModeBar': False,
                                    'staticPlot': True  # Make the plot static
                                },
                                key=f"sparkline_{row['id']}"
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
        st.plotly_chart(fig, use_container_width=True, key="market_cap_chart")

async def main():
    dashboard_placeholder = st.empty()
    
    while True:
        df = await fetch_crypto_data()
        
        if df is not None:
            display_dashboard(df, dashboard_placeholder)
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
