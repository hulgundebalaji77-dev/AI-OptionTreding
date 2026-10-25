import os
import logging
import pandas as pd
import numpy as np
import requests
import streamlit as st
from SmartApi import SmartConnect

# Page Configuration
st.set_page_config(page_title="BALAJI Trading Dashboard", layout="wide")

st.title("📊 BALAJI - Quantitative Trading Dashboard")
st.write("NIFTY Daily Setup (EMA 9, 21, 50, 200 & RSI 14 Scanner)")

# Logging setup
logging.basicConfig(level=logging.INFO)

# Sidebar for Credentials & Settings
st.sidebar.header("🔑 API Credentials")
API_KEY = st.sidebar.text_input("API Key", type="password")
CLIENT_ID = st.sidebar.text_input("Client ID")
PASSWORD = st.sidebar.text_input("Password / MPIN", type="password")
TOTP_TOKEN = st.sidebar.text_input("TOTP Secret Key", type="password")

# Telegram Bot Settings
st.sidebar.header("📱 Telegram Settings")
TELEGRAM_BOT_TOKEN = st.sidebar.text_input("Telegram Bot Token", type="password")
CHAT_ID = st.sidebar.text_input("Telegram Chat ID")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        st.error(f"Telegram Error: {e}")

def calculate_indicators(df):
    # EMA Calculation
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI 14 Calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

if st.sidebar.button("🚀 Run Scanner & Send Alert"):
    if not API_KEY or not CLIENT_ID or not PASSWORD:
        st.warning("कृपया तुमची Angel One API क्रेडेन्शियल्स बरोबर भरा.")
    else:
        try:
            with st.spinner("Connecting to Angel One & Fetching Data..."):
                # Connect to Angel One
                smartApi = SmartConnect(api_key=API_KEY)
                data = smartApi.generateSession(CLIENT_ID, PASSWORD)
                
                if not data or not data.get('status'):
                    st.error(f"Login Failed: {data.get('message', 'Unknown error')}")
                else:
                    st.success("BALAJI Scanner Connected Successfully!")

                    # Nifty 50 Index Parameters (Exchange: NSE, Token: 99926000)
                    exchange = "NSE"
                    symboltoken = "99926000"
                    interval = "ONE_DAY"
                    
                    # Get historical data for Daily timeframe
                    from datetime import datetime, timedelta
                    todays_date = datetime.now().strftime("%Y-%m-%d")
                    past_date = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
                    
                    historicParam = {
                        "exchange": exchange,
                        "symboltoken": symboltoken,
                        "interval": interval,
                        "fromdate": past_date,
                        "todate": todays_date
                    }
                    
                    historical_data = smartApi.getCandleData(historicParam)
                    
                    if historical_data and historical_data.get('status') and historical_data.get('data'):
                        # Format data to DataFrame
                        df = pd.DataFrame(historical_data['data'], columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                        df['close'] = df['close'].astype(float)
                        df['open'] = df['open'].astype(float)
                        df['high'] = df['high'].astype(float)
                        df['low'] = df['low'].astype(float)
                        
                        # Calculate indicators
                        df = calculate_indicators(df)
                        
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        # Display metrics on UI
                        st.subheader("📈 NIFTY Latest Indicators")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Close Price", f"{latest['close']:.2f}")
                        col2.metric("EMA 9", f"{latest['EMA_9']:.2f}")
                        col3.metric("EMA 21", f"{latest['EMA_21']:.2f}")
                        col4.metric("RSI (14)", f"{latest['RSI']:.2f}")
                        
                        msg = (
                            f"*BALAJI NIFTY DAILY SETUP*\n"
                            f"📅 Date: {latest['date']}\n"
                            f"💰 Close: {latest['close']}\n"
                            f"📈 EMA 9: {latest['EMA_9']:.2f}\n"
                            f"📈 EMA 21: {latest['EMA_21']:.2f}\n"
                            f"📈 EMA 50: {latest['EMA_50']:.2f}\n"
                            f"📈 EMA 200: {latest['EMA_200']:.2f}\n"
                            f"📊 RSI (14): {latest['RSI']:.2f}"
                        )
                        
                        # Setup Logic (Crossover condition)
                        if prev['EMA_9'] < prev['EMA_21'] and latest['EMA_9'] > latest['EMA_21']:
                            msg += f"\n\n🚀 *BULLISH CROSSOVER (EMA 9 > EMA 21)*"
                            st.success("Bullish Crossover Detected!")
                            if TELEGRAM_BOT_TOKEN and CHAT_ID:
                                send_telegram_alert(msg)
                        elif prev['EMA_9'] > prev['EMA_21'] and latest['EMA_9'] < latest['EMA_21']:
                            msg += f"\n\n🔻 *BEARISH CROSSOVER (EMA 9 < EMA 21)*"
                            st.warning("Bearish Crossover Detected!")
                            if TELEGRAM_BOT_TOKEN and CHAT_ID:
                                send_telegram_alert(msg)
                        else:
                            st.info("No Crossover Triggered. Current values logged.")
                            if TELEGRAM_BOT_TOKEN and CHAT_ID:
                                send_telegram_alert(msg)
                                
                        # Show raw data table
                        st.dataframe(df.tail(10))
                    else:
                        st.error("Failed to fetch historical candle data.")
        except Exception as e:
            st.error(f"Error in BALAJI scanner: {e}")
