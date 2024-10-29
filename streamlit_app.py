import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio
from datetime import datetime

st.set_page_config(layout="wide")

# Enhanced CSS for better card styling and full-width sparklines
st.markdown("""
<style>
    div[data-testid="stVerticalBlock"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 800px;
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
    
    /* Make Plotly charts expand full width */
    div[data-testid="stColumn"] .stPlotlyChart {
        width: 100% !important;
    }
    
    /* Ensure the Plotly chart container takes full width */
    div[data-testid="stColumn"] .stPlotlyChart > div {
        width: 100% !important;
    }
    
    /* Adjust the SVG within Plotly charts to full width */
    div[data-testid="stColumn"] .stPlotlyChart svg {
        width: 100% !important;
    }
    
    /* Remove any fixed width from the chart wrapper */
    .js-plotly-plot, .plot-container {
        width: 100% !important;
    }    
    .svg-container{
        min-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# Headers for API requests
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def make_api_request(session, url, params=None):
    """Make API request with retry logic and rate limiting"""
    max_retries = 3
    base_delay = 2  # Base delay in seconds
    
    for attempt in range(max_retries):
        try:
            async with session.get(url, params=params, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', base_delay * (attempt + 1)))
                    st.warning(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    st.error(f"API Error: Status code {response.status}")
                    return None
        except asyncio.TimeoutError:
            st.warning(f"Timeout on attempt {attempt + 1}/{max_retries}. Retrying...")
            await asyncio.sleep(base_delay * (attempt + 1))
        except Exception as e:
            st.error(f"Error: {str(e)}")
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
        st.error(f"Error fetching data: {str(e)}")
        return None

def create_sparkline(sparkline_data, coin_id):
    if not sparkline_data or not isinstance(sparkline_data, dict) or 'price' not in sparkline_data:
        return None
    
    prices = sparkline_data['price']
    if not prices or len(prices) == 0:
        return None
        
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        y=prices,
        mode='lines',
        line=dict(
            color='#3366cc',
            width=1.5
        ),
        showlegend=False
    ))
    
    # Set the layout to be minimal and responsive
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=50,  # Keep fixed height for consistency
        autosize=True,  # Enable autosize for responsive width
        yaxis={
            'visible': False,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
        },
        xaxis={
            'visible': False,
            'showgrid': False,
            'zeroline': False,
            'showticklabels': False,
        },
        hovermode=False
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
                        # Create a container for better alignment
                        with st.container():
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
                            
                            # Display sparkline in a container that takes full width
                            try:
                                sparkline_data = row.get('sparkline_in_7d')
                                if sparkline_data is not None:
                                    fig = create_sparkline(sparkline_data, row['id'])
                                    if fig:
                                        st.plotly_chart(
                                            fig,
                                            use_container_width=True,
                                            config={
                                                'displayModeBar': False,
                                                'staticPlot': True,
                                                'responsive': True
                                            },
                                            key=f"sparkline_{row['id']}_{i}_{j}"
                                        )
                            except Exception as e:
                                st.write(f"Error displaying sparkline: {str(e)}")

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
        
        # Update every 5 minutes
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
