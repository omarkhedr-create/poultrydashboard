import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Egypt Poultry Market", page_icon="🐔", layout="wide")

st.title("🇪🇬 Egypt Poultry Market: Live Bourse")
st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} (Cairo Time)")
st.caption("Powered by Google Pipeline. This routes data requests through Google's cloud system to guarantee 100% firewall bypass.")

# PASTE YOUR GOOGLE APPS SCRIPT WEB APP URL HERE
GOOGLE_API_URL = "https://script.google.com/a/macros/thndr.app/s/AKfycbwanyI7c9UJogKJ4JHTTKj0O3cvlkRnrz2Rb9wrrmKozRURKmI8XENl9HV3yWamRCzMrQ/exec"

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def fetch_poultry_prices():
    if GOOGLE_API_URL == "egss":
        st.error("⚠️ Setup needed: Please paste your Google Web App URL into line 13 of app.py!")
        return []
        
    try:
        res = requests.get(GOOGLE_API_URL, timeout=20)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        pass
    return []

# --- DASHBOARD LAYOUT ---
st.header("🛒 Today's Actual Market Prices")
with st.spinner("Fetching exact numerical prices from the Google pipeline..."):
    raw_data = fetch_poultry_prices()
    
    if raw_data:
        # Convert to clean DataFrame
        df = pd.DataFrame(raw_data)
        df.columns = ["Poultry Item", "Exact Price Detail & Numbers"]
        # Remove any internal duplicate lines
        df = df.drop_duplicates(subset=["Exact Price Detail & Numbers"])
        
        st.success("Successfully retrieved exact pricing updates!")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Download data option
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Download Price List as CSV",
            data=csv,
            file_name='egypt_poultry_prices.csv',
            mime='text/csv',
        )
    else:
        st.warning("No live prices returned. Double-check your Google deployment settings.")
