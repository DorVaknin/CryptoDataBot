import pickle
from datetime import timedelta

import gridfs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymongo
import requests


def getXandYWithWindow(klines,scaler,window_size):
    X_y = []
    for i in range(len(closes) - window_size):
        # Stack the lists horizontally
        X = np.column_stack(
            [opens[i:i + window_size], highs[i:i + window_size], lows[i:i + window_size], closes[i:i + window_size],
             volumes[i:i + window_size]])
        # Append the next close value
        y = closes[i + window_size]
        # Append y to X
        X_y.append(np.append(X, y))
    # Convert the sequences to numpy arrays
    X_y = np.array(X_y)
    # Perform the transformation
    X_y_transformed = scaler.transform(X_y)

    # Split the data back into X and y after transformation
    X, y = np.split(X_y_transformed, [-1], axis=-1)

    y = y.ravel()
    return X,y

symbols = ["ETHUSDT"]
# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]
model_collection = db["models"]

# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")

predicted_prices = []
actual_prices = []
interval = "1h"
# Loop over the symbols
for symbol in symbols:
    # Query the collection for the specified symbol and interval
    doc = model_collection.find_one({"symbol": symbol, "interval": interval})

    # Retrieve the model from the GridFS bucket
    model_id = doc["model"]
    klines = []
    indicator_settings = None
    try:
        indicator_settings= doc["indicator_settings"]
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
    except:
        pass
    scaler = None
    try:
        scaler = doc["scaler_x"]
        if scaler:


            scaler = pickle.loads(scaler)
    except:
        pass
    # Get a download stream for the file
    download_stream = model_bucket.open_download_stream(model_id)

    # Read the contents of the stream into a bytes object
    model_bytes = download_stream.read()

    # Deserialize the model using pickle
    model = pickle.loads(model_bytes)

    start = doc.get("latest_timestamp") if doc.get("latest_timestamp") else db["1h"].find({'symbol': symbol}).sort('timestamp', pymongo.DESCENDING).limit(1)[0]['timestamp']
    params = {
        'interval': '1h',
        'limit':1000
    }
    params['symbol'] = symbol
    params['interval'] = interval

    # Set the start and end timestamps
    params['startTime'] = int(start)

    # Send the request and get the response
    response = requests.get("https://api.binance.com/api/v3/klines", params=params)

    # Check the status code of the response
    if response.status_code == 200:

        # Convert the response to a dictionary
        data = response.json()

        # Convert the data to a DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                         'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume',
                                         'taker_buy_quote_asset_volume', 'ignored'])

        # Set the timestamp column as the index
        # df.set_index('timestamp', drop=False, inplace=True)

        # Convert the timestamp column to a datetime
        # df.index = pd.to_datetime(df.index, unit='ms')
        buy_x,buy_y,sell_x,sell_y = [],[],[],[]
        new_close = []

        for timestamp,row in df.iterrows():
            new_close.append(float(row["close"]))
            # Subtract one day from the timestamp
            # close_timestamp =timestamp - timedelta(hours=1)
            input = [[float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),float(row["volume"])]]
            if klines:
                for indicator in indicator_settings:
                    func = eval(indicator.function)
                    func([closes,new_close],**indicator.kwargs)
            if scaler:
                input = scaler.transform([[float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),float(row["volume"]),0.3]])

            # Predict the close price for the next interval
            predicted_price = model.predict([input[0][:-1]])

            input[0][5] = predicted_price
            predicted_price = scaler.inverse_transform(input)[0][5]


            # if predicted_price < row["close"]:
            #     plt.scatter(buy_x, buy_y, c='g', marker='^')
            # Get the actual price from the dataframe
            actual_price = df.shift(-1).iloc[timestamp]['close']
            if actual_price:
                actual_price = float(actual_price)

                # Compare the predicted price with the actual price
                if predicted_price > float(row["close"]) :
                    buy_x.append(timestamp)
                    buy_y.append(predicted_price)
                elif predicted_price < float(row["close"]):
                    sell_x.append(timestamp)
                    sell_y.append(predicted_price)

                # Add the predicted price to the list
                predicted_prices.append(predicted_price)
                # Add the actual price to the list
                actual_prices.append(float(actual_price))

                # input = scaler_x.transform([[float(row["open"]), float(row["high"]), float(row["low"]),
                #                            float(row["close"]), float(row["volume"]), actual_price]])
                # model.fit([input[0][:-1]],[input[0][5]])
                # Plot the predicted prices and actual prices
        plt.scatter(buy_x, buy_y, c='g', marker='^', label='Buy')
        plt.scatter(sell_x, sell_y, c='r', marker='v', label='Sell')
        plt.plot(predicted_prices, label='Predicted')
        plt.plot(actual_prices, label='Actual')
        # Add a legend and show the plot
        plt.legend()
        plt.show()

