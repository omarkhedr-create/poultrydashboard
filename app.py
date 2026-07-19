import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Live & Historical Bourse")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("This dashboard scrapes local agricultural news in real-time to track physical poultry prices.")

# --- SCRAPING FUNCTIONS ---

@st.cache_data(ttl=600)  # Caches live data for 10 minutes
def fetch_live_prices():
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
            
            keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي"]
            found = set()
            for p in paragraphs:
                text = p.get_text()
                for kw in keywords:
                    if kw in text and any(c.isdigit() for c in text) and len(text) < 150:
                        if kw not in found:
                            found.add(kw)
                            prices_data.append({"Poultry Item": kw, "Today's Price Detail": text.strip()})
    except Exception:
        pass
    return prices_data

@st.cache_data(ttl=86400)  # Caches historical data for 24 hours so it doesn't slow down your app
def fetch_historical_prices(pages_to_dig=5):
    base_url = "https://www.elbalad.news"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    historical_data = []
    keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي"]

    for page in range(1, pages_to_dig + 1):
        tag_url = f"{base_url}/tag/7576?page={page}"
        try:
            res = requests.get(tag_url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("a", href=True)
            
            for art in articles:
                link = art["href"]
                # Filter for news articles
                if "/news/" not in link and len(link.split('/')) < 4:
                    continue
                    
                full_link = link if link.startswith("http") else base_url + link
                
                try:
                    art_res = requests.get(full_link, headers=headers, timeout=5)
                    art_soup = BeautifulSoup(art_res.text, "html.parser")
                    
                    date_tag = art_soup.find("time")
                    pub_date = date_tag.text.strip() if date_tag else f"Archive Page {page}"

                    paragraphs = art_soup.find_all(["p", "div", "li"])
                    found_items = set()
                    
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 150:
                            continue
                        for kw in keywords:
                            if kw in text and any(c.isdigit() for c in text):
                                if kw not in found_items:
                                    found_items.add(kw)
                                    historical_data.append({
                                        "Date": pub_date,
                                        "Poultry Item": kw,
                                        "Historical Price": text
                                    })
                    # Brief pause to respect the news server
                    time.sleep(0.3) 
                except Exception:
                    continue
        except Exception:
            continue
            
    return historical_data

# --- DASHBOARD LAYOUT ---

# 1. Live Prices Section
st.header("🛒 Today's Live Market Prices")
with st.spinner("Fetching today's latest prices..."):
    live_data = fetch_live_prices()
    if live_data:
        st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
    else:
        st.warning("Could not parse live prices at the moment. The news source may not have updated yet today.")

st.write("---")

# 2. Historical Prices Section
st.header("🕰️ Historical Prices (Time Machine Scraper)")
st.write("This section digs through past news archives to find older price announcements.")

# Let the user choose how far back to dig using a slider
pages = st.slider("How many pages of news archives should we scan?", min_value=1, max_value=10, value=3)

if st.button("Extract Historical Data"):
    with st.spinner(f"Flipping through {pages} pages of news archives. This may take a minute..."):
        hist_data = fetch_historical_prices(pages_to_dig=pages)
        if hist_data:
            df_hist = pd.DataFrame(hist_data)
            
            # Show a filterable table
            st.success(f"Successfully extracted {len(df_hist)} historical price records!")
            
            # Filter by specific poultry item
            item_filter = st.selectbox("Filter by Item:", ["All"] + list(df_hist["Poultry Item"].unique()))
            if item_filter != "All":
                df_hist = df_hist[df_hist["Poultry Item"] == item_filter]
                
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Allow user to download this custom history directly from the dashboard
            csv = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name='historical_poultry_prices.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical data in the scanned pages.")
