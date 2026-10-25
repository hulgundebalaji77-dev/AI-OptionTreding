import os
import logging
import pandas as pd
import numpy as np
import requests
from SmartApi import SmartConnect

# Logging setup
logging.basicConfig(level=logging.INFO)

# API Credentials
API_KEY = "YOUR_API_KEY"
CLIENT_ID = "YOUR_CLIENT_ID"
PASSWORD = "YOUR_PASSWORD"
TOKEN = "YOUR_TOTP_TOKEN"

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Telegram Error: {e}")

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

def run_balaji_scanner():
    try:
        # Connect to Angel One
        smartApi = SmartConnect(api_key=API_KEY)
        data = smartApi.generateSession(CLIENT_ID, PASSWORD)
        
        if not data['status']:
            print("Login Failed:", data['message'])
            return

        print("BALAJI Scanner Connected Successfully!")

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
        
        if historical_data['status'] and historical_data['data']:
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
                send_telegram_alert(msg)
            elif prev['EMA_9'] > prev['EMA_21'] and latest['EMA_9'] < latest['EMA_21']:
                msg += f"\n\n🔻 *BEARISH CROSSOVER (EMA 9 < EMA 21)*"
                send_telegram_alert(msg)
            else:
                print("No Crossover Triggered. Current values logged.")
                send_telegram_alert(msg)
                
    except Exception as e:
        print(f"Error in BALAJI scanner: {e}")

if __name__ == "__main__":
    run_balaji_scanner()
