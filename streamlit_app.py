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

# First, update the border style function to be simpler
def get_border_class(change_pct):
    """Return the appropriate CSS class based on price change percentage"""
    if change_pct is None:
        return ""
    
    abs_change = abs(change_pct)
    if abs_change >= 9:
        return "change-up-9" if change_pct >= 0 else "change-down-9"
    elif abs_change >= 6:
        return "change-up-6" if change_pct >= 0 else "change-down-6"
    elif abs_change >= 3:
        return "change-up-3" if change_pct >= 0 else "change-down-3"
    return ""

def display_dashboard(df):
    # Add CSS
    st.markdown("""
    <style>
        div[data-testid="column"] > div:first-child {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            height: 100%;
        }
        
        div[data-testid="column"] > div.stBorder {
            border-color: #00ff00 !important;
            border-width: 2px !important;
            border-style: solid !important;
        }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    for idx, coin in df.iterrows():
        with cols[idx % 4]:
            # Create a container with border
            container = st.container()
            container.markdown('<div class="stBorder">', unsafe_allow_html=True)
            
            # Content
            st.image(coin["image"], width=30)
            st.metric(
                label=coin["name"],
                value=f"${coin['current_price']:,.2f}",
                delta=f"{coin['price_change_percentage_24h']:.2f}%",
                delta_color="normal" if coin['price_change_percentage_24h'] >= 0 else "inverse"
            )
            
            if coin.get('sparkline_in_7d'):
                fig = create_sparkline(coin['sparkline_in_7d'])
                if fig:
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            container.markdown('</div>', unsafe_allow_html=True)
            
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
