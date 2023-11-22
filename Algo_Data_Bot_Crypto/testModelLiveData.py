



import pickle
import datetime
import time

import gridfs
import pandas as pd
import pymongo
import requests




import datetime

# Class to represent a trade
class Trade:
  def __init__(self, timestamp, action, amount, price):
    self.timestamp = timestamp
    self.action = action
    self.amount = amount
    self.price = price

  def __repr__(self):
    return f"Trade(timestamp='{self.timestamp}', action='{self.action}', amount={self.amount}, price={self.price})"

# # Initialize a list of trades
# trades = [
#   Trade("2022-01-01 12:00:00", "buy", 2.0, 800),
#   Trade("2022-01-02 12:00:00", "sell", 2.0, 1200),
#   Trade("2022-01-03 12:00:00", "buy", 3.0, 900),
#   Trade("2022-01-04 12:00:00", "sell", 3.0, 1100)
# ]
trades =[]

def calculateTrades():
    # Calculate the total profit or loss of the trades
    profit_loss = 0
    for trade in trades:
      if trade.action == "buy":
        profit_loss -= trade.amount * trade.price
      elif trade.action == "sell":
        profit_loss += trade.amount * trade.price

    # Print the total profit or loss of the trades
    if profit_loss > 0:
      print(" profit:", profit_loss)
    else:
      print(" loss:", profit_loss)
    return  profit_loss












total_profit_loss = 0

symbols = ["ETHBTC"]
# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]
model_collection = db["models"]

# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")

# Loop over the symbols
for symbol in symbols:
    # Query the collection for the specified symbol and interval
    doc = model_collection.find_one({"symbol": symbol, "interval": "1h"})

    # Retrieve the model from the GridFS bucket
    model_id = doc["model"]
    # Get a download stream for the file
    download_stream = model_bucket.open_download_stream(model_id)

    # Read the contents of the stream into a bytes object
    model_bytes = download_stream.read()

    # Deserialize the model using pickle
    model = pickle.loads(model_bytes)




    start = doc.get("latest_timestamp") if doc.get("latest_timestamp") else db["1h"].find({'symbol': symbol}).sort('timestamp', pymongo.DESCENDING).limit(1)[0][
                    'timestamp']
    # start = start + datetime.timedelta(hours=1)
    params = {
        'interval': '1h',
        'limit':1000
    }
    params['symbol'] = symbol

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
        df.set_index('timestamp', drop=False, inplace=True)

        # Convert the timestamp column to a datetime
        df.index = pd.to_datetime(df.index, unit='ms')

        for timestamp,row in df.iterrows():

            if trades:
                trades.append(Trade(timestamp, "sell", 2.0, float(row["close"])))
                total_profit_loss += calculateTrades()
                trades = []
            # Predict the close price for the next interval
            prediction = model.predict([[row["open"],row["high"],row["low"],row["close"]]])

            price = float(row["open"])

            if price < prediction[0]:
                trades.append(Trade(timestamp, "buy", 2.0,price))

    elif response.status_code == 429:
        print(f'retry headers: {response.headers}')
        # Get the retry-after header
        retry_after = response.headers['Retry-After']

        # Sleep for the specified number of seconds
        time.sleep(int(retry_after))
    else:
        # Print the status code and message
        print(response.status_code, response.reason)
    print(f"{total_profit_loss}")







