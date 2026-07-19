import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime
import time

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Live & Historical Bourse")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Powered by API Web Proxies. This fetches the FULL article HTML to extract the actual numerical bullet points while bypassing firewalls.")

# --- PROXY FETCHER (THE FIREWALL BYPASS) ---
@st.cache_data(ttl=600)
def fetch_html_bypassing_firewall(target_url):
    """
    Instead of Streamlit directly visiting the news site (which gets blocked),
    we ask free public proxy APIs to visit the site for us and return the full HTML.
    """
    # We use two different free public proxies to ensure one always works
    proxy_1 = f"https://api.allorigins.win/get?url={urllib.parse.quote(target_url)}"
    proxy_2 = f"https://api.codetabs.com/v1/proxy/?quest={urllib.parse.quote(target_url)}"
    
    try:
        res1 = requests.get(proxy_1, timeout=15)
        if res1.status_code == 200:
            # allorigins returns a JSON with the HTML inside the 'contents' key
            return res1.json().get('contents', '')
    except Exception:
        pass
        
    try:
        res2 = requests.get(proxy_2, timeout=15)
        if res2.status_code == 200:
            # codetabs returns the raw HTML directly
            return res2.text
    except Exception:
        pass
        
    return ""

# --- SCRAPING FUNCTION ---
@st.cache_data(ttl=600)
def extract_exact_prices(pages=1, is_live=True):
    base_url = "https://www.elbalad.news"
    # These keywords help us find the exact bullet points in the article
    keywords = ["البيض الأبيض", "البيض الأحمر", "الكتكوت", "الفراخ البيضاء", "الفراخ البلدي", "كرتونة البيض", "فراخ ساسو"]
    extracted_data = []
    
    for page in range(1, pages + 1):
        # 1. Fetch the archive page via proxy
        tag_url = f"{base_url}/tag/7576?page={page}" if page > 1 else f"{base_url}/tag/7576"
        html = fetch_html_bypassing_firewall(tag_url)
        if not html:
            continue
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 2. Find links to poultry articles
        articles = soup.find_all("a", href=True)
        relevant_links = []
        for art in articles:
            title_text = art.get_text().strip()
            if any(word in title_text for word in ["دواجن", "فراخ", "أسعار", "بورصة"]):
                link = art["href"]
                full_link = link if link.startswith("http") else base_url + link
                if full_link not in relevant_links:
                    relevant_links.append(full_link)
        
        # Limit articles to keep the app fast (1 for today, 2 per page for history)
        limit = 1 if is_live else 2
        
        # 3. Open each article via proxy and get the FULL text
        for full_link in relevant_links[:limit]:
            art_html = fetch_html_bypassing_firewall(full_link)
            if not art_html:
                continue
                
            art_soup = BeautifulSoup(art_html, "html.parser")
            
            # Extract date
            date_tag = art_soup.find("time")
            pub_date = date_tag.text.strip() if date_tag else f"Archive Page {page}"
            
            # 4. Extract bullet points and paragraphs containing prices
            elements = art_soup.find_all(["p", "li", "div", "h3", "h2"])
            found_sentences = set()
            
            for el in elements:
                text = el.get_text().strip()
                # Skip massive paragraphs; we only want the short bullet points with prices
                if len(text) > 150 or len(text) < 10:
                    continue
                    
                for kw in keywords:
                    # CRITICAL: The sentence MUST contain a keyword AND a number!
                    if kw in text and any(char.isdigit() for char in text):
                        if text not in found_sentences:
                            found_sentences.add(text)
                            extracted_data.append({
                                "Date": pub_date,
                                "Category": kw,
                                "Exact Price Detail": text
                            })
            time.sleep(0.5) # Gentle pause between articles
            
    return extracted_data

# --- DASHBOARD LAYOUT ---

# 1. LIVE PRICES
st.header("🛒 Today's Live Market Prices")
with st.spinner("Routing through proxies to read full articles and extract numbers..."):
    live_data = extract_exact_prices(pages=1, is_live=True)
    
    if live_data:
        df_live = pd.DataFrame(live_data).drop_duplicates(subset=["Exact Price Detail"])
        st.success("Successfully extracted exact numbers from today's articles!")
        st.dataframe(df_live, use_container_width=True, hide_index=True)
    else:
        st.warning("Could not extract numbers. The proxies might be temporarily slow.")

st.write("---")

# 2. HISTORICAL PRICES
st.header("🕰️ Historical Prices (Time Machine)")
st.write("This section physically opens past news articles using proxies to extract the exact bullet points containing old prices.")

pages_to_scan = st.slider("How many pages of news archives should we scan?", min_value=1, max_value=10, value=2)

if st.button("Extract Historical Data"):
    with st.spinner(f"Opening articles across {pages_to_scan} pages via proxy. This takes a few seconds..."):
        hist_data = extract_exact_prices(pages=pages_to_scan, is_live=False)
        
        if hist_data:
            df_hist = pd.DataFrame(hist_data).drop_duplicates(subset=["Exact Price Detail"])
            st.success(f"Successfully extracted {len(df_hist)} historical price bullet points!")
            
            # Filter dropdown
            selected_tag = st.selectbox("Filter by Category:", ["All"] + list(df_hist["Category"].unique()))
            if selected_tag != "All":
                df_hist = df_hist[df_hist['Category'] == selected_tag]
                
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Download CSV
            csv = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name=f'poultry_history_exact.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical data. Try increasing the page scan limit.")
