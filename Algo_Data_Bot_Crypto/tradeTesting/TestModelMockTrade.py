import json
import os
import pickle
from datetime import timedelta

import gridfs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymongo
import requests
from sklearn.preprocessing import StandardScaler

from CryptoPortfolio import CryptoPortfolio

def getAllDataWithWindowTransformed(klines, scaler_x, window_size=1):
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]
    X = []
    Y = []
    for i in range(len(closes) - window_size):
        # Stack the lists horizontally
        X.append(np.hstack((opens[i:i + window_size], highs[i:i + window_size], lows[i:i + window_size],
                            closes[i:i + window_size], volumes[i:i + window_size])))
        Y.append(closes[i + window_size])

    Y = np.array(Y)
    Y = Y.reshape(-1, 1)
    scaler_x.fit(X)
    scaler_y.fit(Y)
    X = scaler_x.transform(X)
    Y = scaler_y.transform(Y)

    return X,Y

def getXWithWindowTransformed(klines, scaler_x, window_size):
    klines = klines[-1*window_size:]
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]
    X = np.hstack((opens, highs, lows,
                            closes, volumes))

    X = scaler_x.transform([X])


    return X


client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]
model_collection = db["models"]
symbols = ["SOLBUSD"]
interval = "1d"

# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")
total_portfolio = CryptoPortfolio()

# Loop over the symbols
for symbol in symbols:
    # Query the collection for the specified symbol and interval
    doc = model_collection.find_one({"symbol": symbol, "interval": interval})

    # indicator_settings= doc["indicator_settings"]
    collection = db[interval]
    klines = collection.find({"symbol": symbol})
    klines = list(klines)

    # Extract the timestamp, open, high, low, and close prices from the documents
    timestamps = [kline["timestamp"] for kline in klines]
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]

    # Retrieve the model from the GridFS bucket
    model_id = doc.get("model_id") or doc.get("model")
    window_size = doc.get("window_size")
    scaler_x = doc.get("scaler_x")
    scaler_y = doc.get("scaler_y")
    if scaler_x:
        scaler_x = pickle.loads(scaler_x)
        scaler_y = pickle.loads(scaler_y)
    url = "https://api.binance.com/api/v3/klines?symbol={}&interval={}".format(symbol, interval)
    data_new_klines = requests.get(url).json()
    data_new_klines = data_new_klines[:-1]
    # Convert the data to a DataFrame
    df = pd.DataFrame(data_new_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                     'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume',
                                     'taker_buy_quote_asset_volume', 'ignored'])


    X = getXWithWindowTransformed(klines+data_new_klines, StandardScaler(), window_size)
    model = pickle.loads(model_bucket.find_one({"_id": model_id}).read())
    # Make predictions using the model
    predicted_prices = model.predict(X[-1].reshape(1, -1))
    actual_prices = Y[-1]

    # Unscale the prices
    predicted_prices = scaler_y.inverse_transform(predicted_prices)
    actual_prices = scaler_y.inverse_transform(actual_prices)

    for i in range(len(predicted_prices)):
        if i > 0:
            if predicted_prices[i] > predicted_prices[i-1]:
                total_portfolio.add_buy_order(symbol, 1, actual_prices[i-1])
            elif predicted_prices[i] < predicted_prices[i-1]:
                total_portfolio.add_sell_order(symbol, 1, actual_prices[i-1])
            else:
                print("Price is the same, no action taken")

    # Create a directory for the trade reports if it doesn't exist
    if not os.path.exists("TradeReports"):
        os.makedirs("TradeReports")

    # Save the trade report for the current symbol and interval
    with open("TradeReports/{}_{}_TradeReport.json".format(symbol, interval), "w") as f:
        json.dump(total_portfolio.__dict__, f, indent=4)

# Save the total portfolio report
with open("TradeReports/TotalProtfolio.json", "w") as f:
    json.dump(total_portfolio.__dict__, f, indent=4)
