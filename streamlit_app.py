import streamlit as st
import pandas as pd
import plotly.express as px
import requests

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

# Number of columns for layout
cols_per_row = 3
for i in range(0, len(df), cols_per_row):
    cols = metrics_container.columns(cols_per_row)
    for j in range(cols_per_row):
        if i + j < len(df):
            row = df.iloc[i + j]
            with cols[j]:
                # Format price with appropriate decimal places
                price = f"${row['current_price']:,.2f}"
                
                # Handle None values in price change
                if pd.notna(row['price_change_percentage_24h']):
                    change = f"{row['price_change_percentage_24h']:.2f}%"
                    delta_color = "normal"  # Changed from "increase"/"decrease" to "normal"
                else:
                    change = "N/A"
                    delta_color = "normal"
                
                # Create metric with image
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.metric(
                        label=row["name"],
                        value=price,
                        delta=change,
                        delta_color=delta_color
                    )
                with col2:
                    if pd.notna(row["image"]):
                        st.image(row["image"], width=50)

# Create market cap visualization
st.subheader("Market Cap Comparison")
fig = px.bar(
    df.sort_values("market_cap", ascending=True).tail(20),  # Show top 20 for better visibility
    x="market_cap",
    y="name",
    orientation='h',  # Horizontal bars
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
