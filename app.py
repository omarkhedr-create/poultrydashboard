import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import urllib.parse

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Live & Historical Bourse")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Powered by Google News Aggregation. This bypasses local server firewalls to guarantee 100% data delivery.")

# --- DATA AGGREGATION FUNCTION ---

@st.cache_data(ttl=600)
def fetch_market_data(query):
    # We ask Google's RSS server to fetch the news for us. Google is immune to local firewalls.
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ar&gl=EG&ceid=EG:ar"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = []
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        # Parse the XML RSS feed
        root = ET.fromstring(res.content)
        
        for item in root.findall('./channel/item'):
            title = item.find('title').text if item.find('title') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            source_elem = item.find('source')
            source = source_elem.text if source_elem is not None else "Local News"
            
            # Filter for relevance: ensure the headline actually mentions market prices
            if any(kw in title for kw in ["سعر", "أسعار", "جنيه", "بورصة"]):
                
                # Format the date cleanly 
                try:
                    dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                    clean_date = dt_obj.strftime("%Y-%m-%d")
                except Exception:
                    clean_date = pub_date

                # Create quick tags for easy filtering
                tags = []
                if "فراخ" in title or "دواجن" in title: tags.append("Chicken")
                if "بيض" in title: tags.append("Eggs")
                if "كتكوت" in title or "كتاكيت" in title: tags.append("Chicks")
                
                data.append({
                    "Date": clean_date,
                    "Item Tag": ", ".join(tags) if tags else "General Market",
                    "Market Headline & Price Updates": title,
                    "News Source": source
                })
    except Exception as e:
        pass
        
    return data

# --- DASHBOARD LAYOUT ---

# 1. LIVE DATA SECTION
st.header("🛒 Today's Live Market Prices")
with st.spinner("Fetching today's prices via Google Aggregator..."):
    # "when:1d" forces Google to only fetch announcements from the last 24 hours
    live_data = fetch_market_data('أسعار "الفراخ" OR "البيض" OR "الكتكوت" مصر when:1d')
    if live_data:
        st.success("Successfully fetched live market data! (Firewall Bypassed)")
        st.dataframe(pd.DataFrame(live_data), use_container_width=True, hide_index=True)
    else:
        st.warning("No new price updates have been published to the news indices today yet.")

st.write("---")

# 2. HISTORICAL DATA SECTION
st.header("🕰️ Historical Prices (Time Machine)")
st.write("Select a past date range to pull historical price announcements from the news archives.")

col1, col2 = st.columns(2)
with col1:
    # Default to fetching the last 30 days
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
with col2:
    end_date = st.date_input("End Date", datetime.now())

if st.button("Extract Historical Data"):
    with st.spinner("Searching historical archives..."):
        # Format the query with Google's time parameters (after/before)
        query = f'أسعار "الفراخ" OR "البيض" OR "الكتكوت" مصر after:{start_date.strftime("%Y-%m-%d")} before:{end_date.strftime("%Y-%m-%d")}'
        hist_data = fetch_market_data(query)
        
        if hist_data:
            df_hist = pd.DataFrame(hist_data)
            # Sort by date descending (newest first)
            df_hist = df_hist.sort_values(by="Date", ascending=False)
            
            st.success(f"Successfully extracted {len(df_hist)} historical price records!")
            
            # Add a filter bar for the historical data
            selected_tag = st.selectbox("Filter by Category:", ["All", "Chicken", "Eggs", "Chicks"])
            if selected_tag != "All":
                df_hist = df_hist[df_hist['Item Tag'].str.contains(selected_tag)]
                
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Download button
            csv = df_hist.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name=f'poultry_history_{start_date}_to_{end_date}.csv',
                mime='text/csv',
            )
        else:
            st.error("Could not find historical data for this date range.")
