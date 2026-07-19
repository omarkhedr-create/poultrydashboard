import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time
import cloudscraper

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Live & Historical Bourse")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Powered by Cloudscraper to bypass firewalls and extract exact numerical prices from local markets.")

# Initialize the Cloudflare-bypassing scraper
# This perfectly mimics a standard Windows Chrome browser to trick the firewall
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# --- SCRAPING FUNCTIONS ---

@st.cache_data(ttl=600)
def fetch_exact_prices(pages_to_dig=1, is_live=True):
    base_url = "https://www.elbalad.news"
    keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي"]
    extracted_data = []
    
    for page in range(1, pages_to_dig + 1):
        try:
            # 1. Fetch the news archive page
            tag_url = f"{base_url}/tag/7576?page={page}"
            res = scraper.get(tag_url, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 2. Find links to actual poultry articles
            articles = soup.find_all("a", href=True)
            relevant_links = []
            for art in articles:
                title_text = art.get_text().strip()
                if "دواجن" in title_text or "فراخ" in title_text or "أسعار" in title_text:
                    link = art["href"]
                    full_link = link if link.startswith("http") else base_url + link
                    if full_link not in relevant_links:
                        relevant_links.append(full_link)
            
            # Limit how many articles we check so the app loads fast
            article_limit = 1 if is_live else 3 
            
            # 3. Open the articles and hunt for the numbers
            for full_link in relevant_links[:article_limit]:
                try:
                    art_res = scraper.get(full_link, timeout=10)
                    art_soup = BeautifulSoup(art_res.text, "html.parser")
                    
                    date_tag = art_soup.find("time")
                    pub_date = date_tag.text.strip() if date_tag else datetime.now().strftime("%Y-%m-%d")

                    paragraphs = art_soup.find_all(["p", "div", "h3", "li"])
                    found_items = set()
                    
                    for p in paragraphs:
                        text = p.get_text().strip()
                        # Skip massive paragraphs that aren't price lists
                        if len(text) > 150: 
                            continue
                            
                        for kw in keywords:
                            # CRITICAL CHECK: The paragraph MUST contain the keyword AND a digit (number)
                            if kw in text and any(char.isdigit() for char in text):
                                if kw not in found_items:
                                    found_items.add(kw)
                                    extracted_data.append({
                                        "Date": pub_date,
                                        "Poultry Item": kw,
                                        "Exact Price Detail": text
                                    })
                    time.sleep(0.5) 
                except Exception:
                    continue
        except Exception:
            continue
            
    return extracted_data

# --- DASHBOARD LAYOUT ---

# 1. Live Prices Section
st.header("🛒 Today's Live Market Prices")
with st.spinner("Breaching firewall and reading today's articles for exact numbers..."):
    # Scrape only the first page for the most immediate live data
    live_data = fetch_exact_prices(pages_to_dig=1, is_live=True)
    if live_data:
        st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
    else:
        st.warning("Could not extract numerical prices today. The site might be temporarily down.")

st.write("---")

# 2. Historical Prices Section
st.header("🕰️ Historical Prices (Time Machine Scraper)")
st.write("This section physically opens past news articles and extracts the sentences containing the historical prices.")

pages = st.slider("How many pages of news archives should we scan? (More pages = more history, but takes longer)", min_value=1, max_value=10, value=3)

if st.button("Extract Historical Data"):
    with st.spinner(f"Opening articles across {pages} pages. This takes a few seconds..."):
        hist_data = fetch_exact_prices(pages_to_dig=pages, is_live=False)
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
                file_name='historical_poultry_prices_exact.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical numerical data in the scanned pages.")
