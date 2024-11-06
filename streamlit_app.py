import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
import random

# Initialize cache with 5-minute TTL
cache = TTLCache(maxsize=100, ttl=300)

# Page configuration
st.set_page_config(layout="wide")

# Custom styling with centered content
st.markdown("""
<style>
    #crypto-dashboard {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    div[data-testid="stCaptionContainer"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    div[data-testid="stVerticalBlock"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
        box-sizing: border-box;
    }
    div[data-testid="stColumn"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        color: #000000;
        padding: 1.5rem 1rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 150px;
        gap: 0.5rem;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    
    /* Price change border classes */
    .change-up-3 {
        border: 4px solid #00ff00 !important;
    }
    .change-down-3 {
        border: 4px solid #ff0000 !important;
    }
    .change-up-6 {
        border: 7px solid #00ff00 !important;
    }
    .change-down-6 {
        border: 7px solid #ff0000 !important;
    }
    .change-up-9 {
        border: 10px solid #00ff00 !important;
    }
    .change-down-9 {
        border: 10px solid #ff0000 !important;
    }
    
    /* Center the image container */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    /* Center metric label and value */
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    /* Crypto card styling */
    .crypto-card {
        overflow: hidden;
        box-shadow: 0px 0px 10px gray;
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Chart container styling */
    .chart-container {
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box;
    }
    
    /* Plotly chart specific styling */
    .js-plotly-plot {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .plotly {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .plot-container {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .svg-container {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .main-svg {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Ensure Plotly charts stay within bounds */
    div[data-testid="stColumn"] .stPlotlyChart {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    div[data-testid="stColumn"] .stPlotlyChart > div {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    div[data-testid="stColumn"] .stPlotlyChart svg {
        width: 100% !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    async def wait_if_needed(self):
        now = time.time()
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                st.info(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
                
        self.requests.append(now)

rate_limiter = RateLimiter(max_requests=8, time_window=60)

async def fetch_crypto_data_with_retry(session, url, params):
    """Fetch data with exponential backoff retry logic"""
    max_retries = 5
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            await rate_limiter.wait_if_needed()
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    st.warning(f"Rate limit exceeded. Waiting {delay:.1f} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    st.error(f"API Error: Status {response.status}")
                    return None
                    
        except Exception as e:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            st.error(f"Error: {str(e)}. Retrying in {delay:.1f} seconds...")
            await asyncio.sleep(delay)
    
    return None

async def fetch_crypto_data():
    """Fetch cryptocurrency data with caching"""
    cache_key = 'crypto_data'
    
    if cache_key in cache:
        return cache[cache_key]
    
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': '50',
        'page': '1',
        'sparkline': 'true'
    }
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            data = await fetch_crypto_data_with_retry(session, url, params)
            if data:
                df = pd.DataFrame(data)
                cache[cache_key] = df
                return df
            return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def create_sparkline(sparkline_data):
    """Create a compact sparkline chart"""
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
        height=35,
        autosize=True,
        yaxis={'visible': False, 'showgrid': False, 'zeroline': False},
        xaxis={'visible': False, 'showgrid': False, 'zeroline': False},
        hovermode=False
    )
    
    return fig

def get_price_change_class(price_change):
    """Determine the CSS class based on price change percentage"""
    if price_change is None:
        return ""
    
    abs_change = abs(price_change)
    if abs_change >= 9:
        return "change-up-9" if price_change >= 0 else "change-down-9"
    elif abs_change >= 6:
        return "change-up-6" if price_change >= 0 else "change-down-6"
    elif abs_change >= 3:
        return "change-up-3" if price_change >= 0 else "change-down-3"
    return ""


def display_dashboard(df):
    """Display the cryptocurrency dashboard"""
    st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)
    st.title("Crypto Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown('</div>', unsafe_allow_html=True)

    if df is None or df.empty:
        st.error("No data available. Please try again later.")
        return

    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
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
                        
                        if pd.notna(coin["image"]):
                            st.image(coin["image"], width=30)
                        
                        price = f"${coin['current_price']:,.2f}"
                        change = f"{coin['price_change_percentage_24h']:.2f}%" if pd.notna(coin['price_change_percentage_24h']) else "N/A"
                        delta_color = "normal" if pd.notna(coin['price_change_percentage_24h']) and coin['price_change_percentage_24h'] >= 0 else "inverse"
                        
                        st.metric(
                            label=coin["name"],
                            value=price,
                            delta=change,
                            delta_color=delta_color
                        )
                        
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
                                        'staticPlot': True,
                                        'responsive': True
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
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Main function to run the Streamlit app"""
    # Initialize session state
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now() - timedelta(minutes=6)
    
    # Check if it's time to update (every 5 minutes)
    current_time = datetime.now()
    if (current_time - st.session_state.last_update).total_seconds() >= 300:
        with st.spinner('Updating cryptocurrency data...'):
            df = asyncio.run(fetch_crypto_data())
            if df is not None:
                st.session_state.last_update = current_time
                st.session_state.data = df
    
    # Display dashboard using cached data if available
    if hasattr(st.session_state, 'data'):
        display_dashboard(st.session_state.data)
    else:
        # Initial load
        with st.spinner('Loading cryptocurrency data...'):
            df = asyncio.run(fetch_crypto_data())
            if df is not None:
                st.session_state.data = df
                st.session_state.last_update = current_time
                display_dashboard(df)

if __name__ == "__main__":
    main()
