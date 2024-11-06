import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import aiohttp
import asyncio
from datetime import datetime, timedelta
import time
from cachetools import TTLCache
import random
import base64
import kaleido

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
        # Clean up old requests
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                st.info(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
                
        self.requests.append(now)

# Initialize rate limiter with 8 requests per minute
rate_limiter = RateLimiter(max_requests=8, time_window=60)

async def fetch_crypto_data_with_retry(session, url, params):
    """Fetch data with exponential backoff retry logic"""
    max_retries = 5
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Check rate limit before making request
            await rate_limiter.wait_if_needed()
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Too Many Requests
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
    
    # Return cached data if available
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

def fig_to_svg(fig):
    """Convert Plotly figure to SVG string"""
    try:
        # Use direct image conversion without modifying scope
        svg_bytes = fig.to_image(format='svg', width=150, height=35)
        svg_str = base64.b64encode(svg_bytes).decode()
        return f'data:image/svg+xml;base64,{svg_str}'
    except Exception as e:
        st.warning(f"Failed to generate sparkline: {str(e)}")
        return None

def create_sparkline(sparkline_data):
    """Create a compact sparkline chart and return as SVG"""
    try:
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
            width=150,
            autosize=False,
            yaxis={'visible': False, 'showgrid': False, 'zeroline': False},
            xaxis={'visible': False, 'showgrid': False, 'zeroline': False},
            hovermode=False
        )
        
        return fig_to_svg(fig)
    except Exception as e:
        st.warning(f"Error creating sparkline: {str(e)}")
        return None

def display_dashboard(df):
    """Display the cryptocurrency dashboard"""
    st.title("Crypto Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Base CSS styling for the card layout
    st.markdown("""
    <style>
        .card {
            background-color: white;
            border-radius: 10px;
            padding: 0;
            margin: 0;
            text-align: center;
            max-width: 200px;
        }
        .card img {
            display: block;
            margin: 0 auto;
        }
        .price {
            color: #000000;
            margin: 0 auto;
        }
        .sparkline {
            width: 100%;
            height: 35px;
            margin: 0 auto;
            color: #3d3d3d;
        }
    </style>
    """, unsafe_allow_html=True)

    # Create grid layout in rows of 4
    for i in range(0, len(df), 4):
        row_data = df[i:i+4]
        cols = st.columns(len(row_data))

        for idx, (col, coin) in enumerate(zip(cols, row_data.iterrows())):
            price_change = coin[1].get('price_change_percentage_24h', 0)
            border_color = "#C2ED99" if price_change >= 0 else "#E88687"
            border_width = "4px" if abs(price_change) >= 9 else "3px" if abs(price_change) >= 6 else "2px"
            
            # Generate sparkline SVG
            sparkline_svg = None
            if coin[1].get('sparkline_in_7d'):
                sparkline_svg = create_sparkline(coin[1]['sparkline_in_7d'])
            
            with col:
                # Using st.markdown to render HTML for the card structure with embedded sparkline
                html_content = f'''
                    <div class="card" style="border: {border_width} solid {border_color};">
                        <img src="{coin[1]["image"]}" height="50" width="50" />
                        <h4>{coin[1]["name"]}</h4>
                        <div>
                            <strong class="price">${coin[1]['current_price']:,.2f}</strong>
                            <br />
                            <span style="color: {'#C2ED99' if price_change >= 0 else '#E88687'};">
                                {price_change:.2f}%
                            </span>
                        </div>
                '''
                
                # Add sparkline if available
                if sparkline_svg:
                    html_content += f'<img src="{sparkline_svg}" class="sparkline" />'
                
                html_content += '</div>'
                col.markdown(html_content, unsafe_allow_html=True)

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
