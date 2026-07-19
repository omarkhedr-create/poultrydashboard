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
st.caption("This dashboard aggregates physical poultry prices, using search-engine disguises to bypass cloud firewalls.")

# We disguise the scraper as Google's official indexing bot. Firewalls rarely block Google.
GOOGLEBOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# --- SCRAPING FUNCTIONS ---

@st.cache_data(ttl=600)  
def fetch_live_prices():
    prices_data = []
    keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي"]
    
    # We now check multiple sources to ensure reliability
    sources = [
        {"name": "Elbalad News", "url": "https://www.elbalad.news/tag/7576", "base": "https://www.elbalad.news"},
        {"name": "El Watan News", "url": "https://www.elwatannews.com/tag/8722", "base": "https://www.elwatannews.com"}
    ]
    
    for source in sources:
        try:
            res = requests.get(source["url"], headers=GOOGLEBOT_HEADERS, timeout=10)
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("a", href=True)
            
            target_link = None
            for art in articles:
                title_text = art.get_text()
                if any(word in title_text for word in ["دواجن", "فراخ", "بورصة", "أسعار"]):
                    link = art["href"]
                    target_link = link if link.startswith("http") else source["base"] + link
                    break
                    
            if target_link:
                art_res = requests.get(target_link, headers=GOOGLEBOT_HEADERS, timeout=10)
                art_soup = BeautifulSoup(art_res.text, "html.parser")
                paragraphs = art_soup.find_all(["p", "div", "h2", "h3"])
                
                found = set()
                for p in paragraphs:
                    text = p.get_text().strip()
                    for kw in keywords:
                        if kw in text and any(c.isdigit() for c in text) and len(text) < 150:
                            if kw not in found:
                                found.add(kw)
                                prices_data.append({
                                    "Poultry Item": kw, 
                                    "Today's Price Detail": text,
                                    "Source": source["name"]
                                })
                
                # If we successfully found data from this source, stop searching
                if prices_data:
                    break
                    
        except Exception:
            continue
            
    return prices_data

@st.cache_data(ttl=86400) 
def fetch_historical_prices(pages_to_dig=5):
    historical_data = []
    keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي"]
    base_url = "https://www.elbalad.news"

    for page in range(1, pages_to_dig + 1):
        tag_url = f"{base_url}/tag/7576?page={page}"
        try:
            res = requests.get(tag_url, headers=GOOGLEBOT_HEADERS, timeout=10)
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("a", href=True)
            
            relevant_links = []
            for art in articles:
                title_text = art.get_text().strip()
                if any(word in title_text for word in ["دواجن", "فراخ", "بورصة", "أسعار"]):
                    link = art["href"]
                    full_link = link if link.startswith("http") else base_url + link
                    if full_link not in relevant_links:
                        relevant_links.append(full_link)
            
            for full_link in relevant_links[:2]:
                try:
                    art_res = requests.get(full_link, headers=GOOGLEBOT_HEADERS, timeout=7)
                    art_soup = BeautifulSoup(art_res.text, "html.parser")
                    
                    date_tag = art_soup.find("time")
                    pub_date = date_tag.text.strip() if date_tag else f"Archive Page {page}"

                    paragraphs = art_soup.find_all(["p", "div", "h2", "h3"])
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
                    time.sleep(0.5) # Gentle pacing
                except Exception:
                    continue
        except Exception:
            continue
            
    return historical_data

# --- DASHBOARD LAYOUT ---

st.header("🛒 Today's Live Market Prices")
with st.spinner("Bypassing firewalls & fetching today's latest prices..."):
    live_data = fetch_live_prices()
    if live_data:
        st.success("Successfully fetched live market data!")
        st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
    else:
        st.warning("Could not parse live prices. Both primary and backup news sources blocked the server request.")

st.write("---")

st.header("🕰️ Historical Prices (Time Machine Scraper)")
st.write("This section digs through past news archives to find older price announcements.")

pages = st.slider("How many pages of news archives should we scan?", min_value=1, max_value=10, value=3)

if st.button("Extract Historical Data"):
    with st.spinner(f"Flipping through {pages} pages of news archives. This will only take a few seconds..."):
        hist_data = fetch_historical_prices(pages_to_dig=pages)
        if hist_data:
            df_hist = pd.DataFrame(hist_data)
            
            st.success(f"Successfully extracted {len(df_hist)} historical price records!")
            
            item_filter = st.selectbox("Filter by Item:", ["All"] + list(df_hist["Poultry Item"].unique()))
            if item_filter != "All":
                df_hist = df_hist[df_hist["Poultry Item"] == item_filter]
                
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            csv = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name='historical_poultry_prices.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical data. The cloud server is still being heavily filtered.")
