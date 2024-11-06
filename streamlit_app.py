import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime

# Page configuration
st.set_page_config(layout="wide")

# Custom styling for better card and chart containment
st.markdown("""
<style>
    .crypto-card {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px;
        margin: 5px;
    }
    .stMetric {
        margin-bottom: 0.5rem;
    }
    .chart-container {
        margin-top: -15px;  /* Reduce space between metric and chart */
    }
    /* Ensure charts stay within their containers */
    .stPlotlyChart {
        width: 100% !important;
    }
    /* Adjust metric value size */
    .metric-value {
        font-size: 0.9rem !important;
    }
    /* Container padding adjustments */
    div[data-testid="column"] {
        padding: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

async def fetch_crypto_data():
    """Fetch cryptocurrency data from CoinGecko API"""
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': '100',
        'page': '1',
        'sparkline': 'true'
    }
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return pd.DataFrame(data)
                else:
                    st.error(f"API Error: Status code {response.status}")
                    return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def create_sparkline(sparkline_data):
    """Create a compact sparkline chart for price history"""
    if not sparkline_data or not isinstance(sparkline_data, dict) or 'price' not in sparkline_data:
        return None
    
    prices = sparkline_data['price']
    if not prices or len(prices) == 0:
        return None
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=prices,
        mode='lines',
        line=dict(color='#3366cc', width=1),
        showlegend=False
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=35,  # Reduced height for better fit
        autosize=True,
        yaxis={
            'visible': False,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'fixedrange': True
        },
        xaxis={
            'visible': False,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
            'fixedrange': True
        },
        hovermode=False
    )
    
    return fig

def display_dashboard(df):
    """Display the cryptocurrency dashboard"""
    st.title("Crypto Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Display crypto metrics in a grid
    cols_per_row = 4
    for i in range(0, len(df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(df):
                coin = df.iloc[i + j]
                with col:
                    with st.container():
                        st.markdown('<div class="crypto-card">', unsafe_allow_html=True)
                        
                        # Coin image and basic info
                        if pd.notna(coin["image"]):
                            st.image(coin["image"], width=30)
                        
                        # Price and change metrics
                        price = f"${coin['current_price']:,.2f}"
                        change = f"{coin['price_change_percentage_24h']:.2f}%" if pd.notna(coin['price_change_percentage_24h']) else "N/A"
                        delta_color = "normal" if pd.notna(coin['price_change_percentage_24h']) and coin['price_change_percentage_24h'] >= 0 else "inverse"
                        
                        st.metric(
                            label=coin["name"],
                            value=price,
                            delta=change,
                            delta_color=delta_color
                        )
                        
                        # Sparkline chart
                        sparkline_data = coin.get('sparkline_in_7d')
                        if sparkline_data is not None:
                            fig = create_sparkline(sparkline_data)
                            if fig:
                                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                                st.plotly_chart(
                                    fig,
                                    use_container_width=True,
                                    config={
                                        'displayModeBar': False,
                                        'staticPlot': True
                                    }
                                )
                                st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

    # Market Cap Comparison
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

def main():
    """Main function to run the Streamlit app"""
    if 'update_counter' not in st.session_state:
        st.session_state.update_counter = 0

    # Fetch and display data
    df = asyncio.run(fetch_crypto_data())
    if df is not None:
        display_dashboard(df)
    
    # Auto-refresh every 5 minutes
    st.session_state.update_counter += 1
    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
    st.rerun()

if __name__ == "__main__":
    import time
    main()
