import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Custom CSS for card styling
st.markdown("""
<style>
    [data-testid="stVerticalBlock"] {
        background-color: white;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
    }
    
    /* Remove default container padding to prevent double padding */
    [data-testid="stHorizontalBlock"] {
        padding: 0 !important;
        gap: 0.5rem !important;
    }
    
    /* Ensure metrics are properly spaced */
    [data-testid="metric-container"] {
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# API call to get crypto data
url = 'https://api.coingecko.com/api/v3/coins/markets'
params = {
    'vs_currency': 'usd',
    'order': 'market_cap_desc',
    'per_page': 100,
    'page': 1,
    'sparkline': False
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data)
except requests.exceptions.RequestException as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# Streamlit UI
st.title("Crypto Dashboard")

# Process data in chunks of 4 for each row
for i in range(0, len(df), 4):
    row_data = df.iloc[i:i+4]
    
    # Create a row container
    cols = st.columns(4)
    
    # Fill each column with a card
    for idx, (_, row) in enumerate(row_data.iterrows()):
        with cols[idx]:
            with st.container():
                # Center the image
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if pd.notna(row["image"]):
                        st.image(row["image"], width=50)
                
                # Format price and change
                price = f"${row['current_price']:,.2f}"
                if pd.notna(row['price_change_percentage_24h']):
                    change = f"{row['price_change_percentage_24h']:.2f}%"
                    delta_color = "normal"
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

# Add some space before the chart
st.markdown("---")

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
