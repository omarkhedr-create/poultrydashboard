# Save the dashboard code into a local file called app.py inside the notebook environment
%%writefile app.py
# Install the missing package with the required '!' prefix for Colab
!pip install streamlit -q

# Test if it worked
import streamlit as st
print("Streamlit successfully installed! 🎉")
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="Egypt Poultry Live Dashboard", page_icon="🐔", layout="wide")
st.title("🇪🇬 Egypt Poultry Live Dashboard")

# (The rest of the dashboard code goes here...)
st.write("Dashboard script successfully saved!")

# Page configuration
st.set_page_config(page_title="Egypt Poultry Live Dashboard", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry & Financial Market Dashboard")
st.write(f"**Last Lively Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Refresh the page anytime to trigger a fresh live scrape.")

# --- DATA RETRIEVAL FUNCTIONS ---
@st.cache_data(ttl=600)  # Caches data for 10 minutes to stay fast but fresh
def fetch_stock_live(ticker):
    stock = yf.Ticker(ticker)
    recent = stock.history(period="5d")
    if recent.empty:
        return "N/A", "N/A"
    return recent["Close"].iloc[-1], recent["Volume"].iloc[-1]

@st.cache_data(ttl=3600)  # Caches historical chart data for 1 hour
def fetch_stock_history(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y").reset_index()
    if not hist.empty:
        hist['Date'] = hist['Date'].dt.date
    return hist

@st.cache_data(ttl=600)
def fetch_physical_prices():
    base_url = "https://www.elbalad.news"
    tag_url = f"{base_url}/tag/7576"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    prices_data = []
    
    try:
        res = requests.get(tag_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        latest_art = soup.find("a", href=True, title=True)
        if latest_art:
            link = latest_art["href"] if latest_art["href"].startswith("http") else base_url + latest_art["href"]
            art_res = requests.get(link, headers=headers, timeout=10)
            art_soup = BeautifulSoup(art_res.text, "html.parser")
            paragraphs = art_soup.find_all(["p", "div"])
            
            keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء"]
            found = set()
            for p in paragraphs:
                text = p.get_text()
                for kw in keywords:
                    if kw in text and any(c.isdigit() for c in text) and len(text) < 150:
                        if kw not in found:
                            found.add(kw)
                            prices_data.append({"Poultry Item": kw, "Latest Live Update Details": text.strip()})
    except Exception as e:
        pass
    return prices_data

# --- LAYOUT CREATION ---
col1, col2 = st.columns([1, 1.5])

with col1:
    st.header("🛒 Live Physical Poultry Bourse")
    with st.spinner("Scraping local market prices..."):
        physical_data = fetch_physical_prices()
        if physical_data:
            st.dataframe(pd.DataFrame(physical_data), use_container_width=True, hide_index=True)
        else:
            st.warning("Could not parse physical prices from agricultural feeds right now.")

    st.write("---")
    st.header("📈 Live EGX Financial Stocks")
    
    # Cairo Poultry
    poul_price, poul_vol = fetch_stock_live("POUL.CA")
    c1, c2 = st.columns(2)
    c1.metric(label="Cairo Poultry (POUL)", value=f"{poul_price:.2f} EGP" if isinstance(poul_price, float) else poul_price)
    c2.metric(label="POUL Volume Today", value=f"{int(poul_vol):,}" if isinstance(poul_vol, (int, float)) else poul_vol)
    
    # Egypt for Poultry
    epco_price, epco_vol = fetch_stock_live("EPCO.CA")
    c3, c4 = st.columns(2)
    c3.metric(label="Egypt for Poultry (EPCO)", value=f"{epco_price:.2f} EGP" if isinstance(epco_price, float) else epco_price)
    c4.metric(label="EPCO Volume Today", value=f"{int(epco_vol):,}" if isinstance(epco_vol, (int, float)) else epco_vol)

with col2:
    st.header("📊 Interactive Historical Charts (1-Year)")
    
    selected_stock = st.selectbox("Choose a stock to view history:", ["Cairo Poultry (POUL.CA)", "Egypt for Poultry (EPCO.CA)"])
    ticker_to_chart = "POUL.CA" if "Cairo" in selected_stock else "EPCO.CA"
    
    hist_df = fetch_stock_history(ticker_to_chart)
    if not hist_df.empty:
        # Streamlit automatically builds a beautiful interactive line chart
        st.line_chart(data=hist_df, x="Date", y="Close", use_container_width=True)
        
        with st.expander("View Raw Data Table"):
            st.dataframe(hist_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].sort_values(by="Date", ascending=False), hide_index=True)
    else:
        st.error("Could not render history graph.")
