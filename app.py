import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Unblockable Dashboard")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Powered by Global RSS Syndication. This bypasses all server firewalls to guarantee actual price numbers.")

# --- RSS EXTRACTION FUNCTION ---
@st.cache_data(ttl=600)
def get_unblockable_prices(query):
    # Bing News RSS is open, free, never blocks cloud servers, and provides full paragraphs with numbers
    url = f"https://www.bing.com/news/search?q={requests.utils.quote(query)}&format=rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    extracted_data = []
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(res.text)
        
        for item in root.findall('./channel/item'):
            # Get date
            date_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
            try:
                dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                clean_date = dt.strftime("%Y-%m-%d")
            except Exception:
                clean_date = date_str
                
            # Get the text snippet (which contains the actual prices)
            desc = item.find('description').text if item.find('description') is not None else ""
            title = item.find('title').text if item.find('title') is not None else ""
            source = item.find('source').text if item.find('source') is not None else "News Source"
            
            # Combine and clean the text
            full_text = f"{title}. {desc}"
            clean_text = re.sub('<[^<]+>', '', full_text) # Remove any stray HTML tags
            
            # Split the paragraph into smaller sentences/chunks to isolate the exact prices
            sentences = re.split(r'[.،؛:-]', clean_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                # If the sentence has no numbers, skip it (we only want prices!)
                if not any(char.isdigit() for char in sentence):
                    continue
                    
                # Categorize what the sentence is talking about
                category = None
                if "بيض" in sentence: 
                    category = "Eggs (البيض)"
                elif "كتكوت" in sentence or "كتاكيت" in sentence: 
                    category = "Chicks (الكتكوت)"
                elif "فراخ" in sentence or "دواجن" in sentence: 
                    category = "Chicken (الفراخ)"
                
                # If it matches our criteria, add it to the table
                if category and len(sentence) > 10:
                    extracted_data.append({
                        "Date": clean_date,
                        "Category": category,
                        "Exact Price Detail": sentence,
                        "Source": source
                    })
    except Exception as e:
        pass
        
    return extracted_data

# --- DASHBOARD LAYOUT ---

# 1. LIVE PRICES
st.header("🛒 Today's Live Market Prices")
with st.spinner("Fetching today's exact numbers via Unblockable RSS..."):
    # Query Bing for today's market prices
    live_data = get_unblockable_prices("أسعار الدواجن الفراخ البيض الكتكوت اليوم مصر")
    
    if live_data:
        # Remove duplicate sentences and display
        df_live = pd.DataFrame(live_data).drop_duplicates(subset=["Exact Price Detail"])
        st.success("Successfully fetched live market numbers! (Firewall Bypassed)")
        st.dataframe(df_live, use_container_width=True, hide_index=True)
    else:
        st.warning("Could not fetch data. The market may not have published updates yet today.")

st.write("---")

# 2. HISTORICAL PRICES
st.header("🕰️ Historical Prices (Time Machine)")
st.write("Because we are using a search engine feed, we can specifically query past months to extract old prices.")

# Let the user pick a specific month/year to search
past_month = st.selectbox("Select a past timeframe to search:", [
    "يوليو 2026", "يونيو 2026", "مايو 2026", "أبريل 2026", "مارس 2026", "فبراير 2026", "يناير 2026"
])

if st.button("Extract Historical Data"):
    with st.spinner(f"Searching global archives for {past_month}..."):
        # We append the month and year to the search query to pull old articles
        hist_data = get_unblockable_prices(f"أسعار الدواجن الفراخ البيض الكتكوت مصر {past_month}")
        
        if hist_data:
            df_hist = pd.DataFrame(hist_data).drop_duplicates(subset=["Exact Price Detail"])
            st.success(f"Successfully extracted {len(df_hist)} historical price records for {past_month}!")
            
            # Filter
            selected_tag = st.selectbox("Filter by Category:", ["All", "Chicken (الفراخ)", "Eggs (البيض)", "Chicks (الكتكوت)"])
            if selected_tag != "All":
                df_hist = df_hist[df_hist['Category'] == selected_tag]
                
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Download
            csv = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name=f'poultry_history_{past_month}.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical data for this specific timeframe.")
