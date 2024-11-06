import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime
import uuid

# Generate a unique session ID at app start
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.set_page_config(layout="wide")

# [Previous CSS styles remain unchanged]
st.markdown("""
<style>
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
    /* [Rest of the CSS remains the same] */
</style>
""", unsafe_allow_html=True)

HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def generate_unique_key(base_name, *args):
    """Generate a unique key for Streamlit elements"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"{st.session_state.session_id}_{base_name}_{'_'.join(str(arg) for arg in args)}_{timestamp}"

async def make_api_request(session, url, params=None):
    """Make API request with retry logic and rate limiting"""
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with session.get(url, params=params, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', base_delay * (attempt + 1)))
                    warning_key = generate_unique_key('warning', 'rate_limit', attempt)
                    st.warning(f"Rate limit exceeded. Waiting {retry_after} seconds...", key=warning_key)
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    error_key = generate_unique_key('error', 'api', response.status)
                    st.error(f"API Error: Status code {response.status}", key=error_key)
                    return None
        except Exception as e:
            error_key = generate_unique_key('error', 'request', attempt)
            st.error(f"Error: {str(e)}", key=error_key)
            return None
    
    return None

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
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            data = await make_api_request(session, url, params)
            if data:
                return pd.DataFrame(data)
            return None
    except Exception as e:
        error_key = generate_unique_key('error', 'fetch')
        st.error(f"Error fetching data: {str(e)}", key=error_key)
        return None

def create_sparkline(sparkline_data, coin_id):
    if not sparkline_data or not isinstance(sparkline_data, dict) or 'price' not in sparkline_data:
        return None
    
    prices = sparkline_data['price']
    if not prices or len(prices) == 0:
        return None
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=prices,
        mode='lines',
        line=dict(color='#3366cc', width=1.5),
        showlegend=False
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=50,
        autosize=True,
        yaxis={'visible': False, 'showgrid': False, 'zeroline': False, 'showticklabels': False},
        xaxis={'visible': False, 'showgrid': False, 'zeroline': False, 'showticklabels': False},
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

def display_dashboard(df, placeholder):
    with placeholder.container():
        title_key = generate_unique_key('title')
        st.title("Crypto Dashboard", key=title_key)
        
        caption_key = generate_unique_key('caption')
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", key=caption_key)

        metrics_container = st.container()

        cols_per_row = 4
        for i in range(0, len(df), cols_per_row):
            cols = metrics_container.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(df):
                    row = df.iloc[i + j]
                    with cols[j]:
                        price_change_class = get_price_change_class(row['price_change_percentage_24h'])
                        
                        container_key = generate_unique_key('card', row['id'], i, j)
                        with st.container():
                            if pd.notna(row["image"]):
                                image_key = generate_unique_key('image', row['id'], i, j)
                                st.image(row["image"], width=50, key=image_key)
                            
                            price = f"${row['current_price']:,.2f}"
                            if pd.notna(row['price_change_percentage_24h']):
                                change = f"{row['price_change_percentage_24h']:.2f}%"
                                delta_color = "normal" if row['price_change_percentage_24h'] >= 0 else "inverse"
                            else:
                                change = "N/A"
                                delta_color = "normal"
                            
                            metric_key = generate_unique_key('metric', row['id'], i, j)
                            st.metric(
                                label=row["name"],
                                value=price,
                                delta=change,
                                delta_color=delta_color,
                                key=metric_key
                            )
                            
                            try:
                                sparkline_data = row.get('sparkline_in_7d')
                                if sparkline_data is not None:
                                    fig = create_sparkline(sparkline_data, row['id'])
                                    if fig:
                                        chart_key = generate_unique_key('sparkline', row['id'], i, j)
                                        st.plotly_chart(
                                            fig,
                                            use_container_width=True,
                                            config={'displayModeBar': False, 'staticPlot': True, 'responsive': True},
                                            key=chart_key
                                        )
                            except Exception as e:
                                error_key = generate_unique_key('error', 'sparkline', row['id'])
                                st.write(f"Error displaying sparkline: {str(e)}", key=error_key)

        market_cap_key = generate_unique_key('market_cap')
        st.subheader("Market Cap Comparison", key=market_cap_key)
        
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
        chart_key = generate_unique_key('market_cap_chart')
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

async def main():
    dashboard_placeholder = st.empty()
    
    while True:
        df = await fetch_crypto_data()
        
        if df is not None:
            display_dashboard(df, dashboard_placeholder)
        
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
