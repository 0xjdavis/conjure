import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Add custom CSS for card styling
st.markdown("""
<style>
    .crypto-card {
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
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
    response.raise_for_status()  # Check for HTTP errors
    data = response.json()
    df = pd.DataFrame(data)
except requests.exceptions.RequestException as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# Streamlit UI
st.title("Crypto Dashboard")

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
                # Create a card container with border
                st.markdown('<div class="crypto-card">', unsafe_allow_html=True)
                
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
                
                # Close the card container
                st.markdown('</div>', unsafe_allow_html=True)

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

# Update layout for better visualization
fig.update_layout(
    height=600,
    xaxis_title="Market Cap (USD)",
    yaxis_title="Cryptocurrency",
    showlegend=False
)

# Format market cap values
fig.update_xaxes(tickformat="$.2s")

st.plotly_chart(fig, use_container_width=True)
