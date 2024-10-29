import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime

st.set_page_config(layout="wide")

# Updated CSS for better card and sparkline container handling
st.markdown("""
<style>
    div[data-testid="stColumn"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        color: #000000;
        padding: 1rem;
        text-align: center;
    }
    
    div[data-testid="stMetric"] {
        margin-bottom: 0.5rem;
    }
    
    .sparkline-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 60px;
        margin: 0 auto;
    }
    
    .element-container {
        margin-bottom: 0.5rem;
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
        'sparkline': 'true'
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

def create_sparkline(prices, coin_id):
    if not prices or len(prices) < 2:
        return None
    
    # Calculate price change for color
    price_change = prices[-1] - prices[0]
    line_color = '#00ff00' if price_change >= 0 else '#ff0000'
    
    fig = go.Figure()
    
    # Add price line with improved styling
    fig.add_trace(go.Scatter(
        y=prices,
        mode='lines',
        line=dict(
            color=line_color,
            width=1.5
        ),
        fill='tonexty',
        fillcolor=f'rgba{tuple(int(line_color[i:i+2], 16) for i in (1, 3, 5)) + (0.2,)}'
    ))
    
    # Enhanced layout configuration
    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=4),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=50,
        width=150,
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=True
        ),
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=True
        ),
        hovermode=False,
        showlegend=False
    )
    
    return fig

def display_dashboard(df, placeholder):
    with placeholder.container():
        st.title("Crypto Dashboard")
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
                        # Display logo
                        if pd.notna(row["image"]):
                            st.image(row["image"], width=50)
                        
                        # Format price
                        price = f"${row['current_price']:,.2f}"
                        
                        # Handle price change
                        if pd.notna(row['price_change_percentage_24h']):
                            change = f"{row['price_change_percentage_24h']:.2f}%"
                            delta_color = "normal" if row['price_change_percentage_24h'] >= 0 else "inverse"
                        else:
                            change = "N/A"
                            delta_color = "normal"
                        
                        # Display metric
                        st.metric(
                            label=row["name"],
                            value=price,
                            delta=change,
                            delta_color=delta_color
                        )
                        
                        # Display sparkline with improved error handling
                        try:
                            sparkline_data = row['sparkline_in_7d'].get('price', [])
                            if sparkline_data and len(sparkline_data) > 1:
                                fig = create_sparkline(sparkline_data, row['id'])
                                if fig:
                                    with st.container():
                                        st.plotly_chart(
                                            fig,
                                            use_container_width=True,
                                            config={
                                                'displayModeBar': False,
                                                'staticPlot': True
                                            }
                                        )
                        except (AttributeError, KeyError) as e:
                            st.write("No sparkline data available")

        # Market cap visualization
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
    dashboard_placeholder = st.empty()
    
    while True:
        df = await fetch_crypto_data()
        
        if df is not None:
            display_dashboard(df, dashboard_placeholder)
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
