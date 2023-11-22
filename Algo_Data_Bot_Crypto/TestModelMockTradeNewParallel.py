import re
from concurrent.futures import wait, ProcessPoolExecutor
from datetime import datetime
import os
import pickle
from datetime import timedelta
from multiprocessing import freeze_support, Manager

import gridfs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymongo
import requests
from sklearn.preprocessing import StandardScaler

from tradeStrategy.BaseTradeStrategy import TradeStratagyAboveThreshold, TradeStratagyWithIndicators, BaseTradeStrategy, \
    TradeStrategyDropThreshold, TradeStrategySellWithIndicators, TradeStrategySellWithIndicatorsWithThreshold
from tradeTesting.CryptoPortfolio import CryptoPortfolio
from tradeTesting.CryptoPortfolioParallell import CryptoPortfolioParallell

def percent_change(old_value, new_value):
  return ((new_value - old_value) / old_value) * 100

def getXWithWindowTransformed(klines,scaler_x, window_size):
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

def getAllDataWithWindowTransformed(klines, window_size):
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

    return X,Y,scaler_x,scaler_y


interval = "1d"
symbols = ["SOLBUSD"]
invest_in_usd_each_symbol = 10
retrain_model = False
# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]
models_db_name = "models_until_2023_dynamic_window_size"
model_collection = db[models_db_name]

symbols = model_collection.distinct("symbol")
pattern = '(BUSD|USDT)$'
symbols = [s for s in symbols if re.search(pattern, s)]
symbols_count = {}
for symbol in symbols:
    base_symbol = re.sub(pattern, '', symbol)
    if base_symbol in symbols_count:
        symbols_count[base_symbol].append(symbol)
    else:
        symbols_count[base_symbol] = [symbol]
# filter duplicate symbols
symbols = [symbols_count[base_symbol][0] for base_symbol in symbols_count if len(symbols_count[base_symbol]) > 0]

# symbols = model_collection.find({"interval": interval,"symbol" : {"$in": symbols}},{"symbol": 1}).sort("score", pymongo.DESCENDING).limit(90)
# symbols = [doc["symbol"] for doc in list(symbols)]

# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, models_db_name)

predicted_prices = []
actual_prices = []

# max_timestamp = 1642510590000
max_timestamp = None
trade_stategy = TradeStrategySellWithIndicatorsWithThreshold(45)
retrain_interval = 10
def processSymbol(symbol, trade_report_dir):
    # Query the collection for the specified symbol and interval
    doc = model_collection.find_one({"symbol": symbol, "interval": interval})
    start = doc.get("latest_timestamp") if doc.get("latest_timestamp") else \
        db[interval].find({'symbol': symbol}).sort('timestamp', pymongo.DESCENDING).limit(1)[0]['timestamp']
    score = doc.get("score")
    if doc and score > 0.85:
        # Retrieve the model from the GridFS bucket
        model_id = doc.get("model_id") or doc.get("model")
        klines = []
        indicator_settings = None
        try:
            window_size = doc["window_size"]
            # window_size = 20
        except:
            pass
        try:
            # indicator_settings= doc["indicator_settings"]
            collection = db[interval]
            if start:
                klines = collection.find({"symbol": symbol, "timestamp": {"$lt": start}})
            else:
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
        scaler_x = None
        scaler_y = None
        try:
            scaler_x = doc["scaler_x"]
            scaler_y = doc["scaler_y"]
            if scaler_x:
                scaler_x = pickle.loads(scaler_x)
                scaler_y = pickle.loads(scaler_y)
        except:
            return
        try:
            # Get a download stream for the file
            download_stream = model_bucket.open_download_stream(model_id)
        except:
            return

        # Read the contents of the stream into a bytes object
        model_bytes = download_stream.read()

        # Deserialize the model using pickle
        model = pickle.loads(model_bytes)


        params = {
            'interval': interval,
            'limit': 1000
        }
        params['symbol'] = symbol
        params['interval'] = interval

        # Set the start and end timestamps
        params['startTime'] = int(start)
        params['endTime'] = max_timestamp

        # Send the request and get the response
        response = requests.get("https://api.binance.com/api/v3/klines", params=params)

        if retrain_model:
            scaler_x = None
            scaler_y = None
            all_input, y, scaler_x, scaler_y = getAllDataWithWindowTransformed(klines , window_size)
            try:
                model = type(model)()
            except:
                try:
                    model = type(model)(**model.get_params())
                except:
                    try:
                        model = model.clone()
                    except:
                        old_model = model
                        model = type(model)(estimators=old_model.estimators, weights=old_model.weights)
                        # model.weights = old_model.weights
                        # model.voting = old_model.voting
            model.fit(all_input, y.ravel())
        # Check the status code of the response
        if response.status_code == 200:

            # Convert the response to a dictionary
            data = response.json()

            data = data[:-1]
            # Convert the data to a DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                             'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume',
                                             'taker_buy_quote_asset_volume', 'ignored'])

            # Set the timestamp column as the index
            # df.set_index('timestamp', drop=False, inplace=True)

            # Convert the timestamp column to a datetime
            # df.index = pd.to_datetime(df.index, unit='ms')
            buy_x, buy_y, sell_x, sell_y = [], [], [], []
            new_close = []
            all_new_rows = []
            predicted_price = None
            old_predict = None
            old_actual_price = None
            symbol_portfolio = CryptoPortfolio()
            for timestamp, row in df.iterrows():
                all_new_rows.append(row.to_dict())
                new_close.append(float(row["close"]))
                # Subtract one day from the timestamp
                # close_timestamp =timestamp - timedelta(hours=1)
                input = [[float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),
                          float(row["volume"])]]
                # if klines:
                #     for indicator in indicator_settings:
                #         func = eval(indicator.function)
                #         func([closes,new_close],**indicator.kwargs)
                if scaler_x:
                    input = getXWithWindowTransformed(klines + all_new_rows,scaler_x, window_size)
                    # input = scaler_x.transform([[float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), float(row["volume"]), 0.3]])
                if predicted_price:
                    old_predict = predicted_price
                try:
                    # Predict the close price for the next interval
                    predicted_price = model.predict(input)
                except:
                    continue

                predicted_price = scaler_y.inverse_transform([predicted_price])[0][-1]

                if old_predict and timestamp + 1 < len(df):
                    if predicted_price > old_predict:
                        trade_stategy.buy_strategy(klines + all_new_rows,symbol_portfolio,symbol,predicted_price,old_predict,actual_price,invest_in_usd_each_symbol)
                    elif predicted_price < old_predict:
                        trade_stategy.sell_strategy(klines +all_new_rows,symbol_portfolio,symbol,predicted_price,old_predict,actual_price)

                actual_price = df.shift(-1).iloc[timestamp]['close']
                if actual_price:
                    actual_price = float(actual_price)

                # if old_actual_price and actual_price:
                #     actual_prices.append(((actual_price - old_actual_price) / old_actual_price) * 100)

                # if predicted_price < row["close"]:
                #     plt.scatter(buy_x, buy_y, c='g', marker='^')
                # Get the actual price from the dataframe

                predicted_prices.append(predicted_price)
                if actual_price:
                    actual_price = float(actual_price)

                    # Add the predicted price to the list

                    # Add the actual price to the list
                    actual_prices.append(float(actual_price))

                    # input = scaler_x.transform([[float(row["open"]), float(row["high"]), float(row["low"]),
                    #                            float(row["close"]), float(row["volume"]), actual_price]])
                    if retrain_model and timestamp % retrain_interval == 0:
                        scaler_x=None
                        scaler_y =None
                        all_input, y,scaler_x,scaler_y = getAllDataWithWindowTransformed(klines + all_new_rows, window_size)
                        try:
                            model = type(model)()
                        except:
                            try:
                                model = type(model)(**model.get_params())
                            except:
                                try:
                                    model = model.clone()
                                except:
                                    old_model = model
                                    model = type(model)(estimators=old_model.estimators, weights=old_model.weights)
                                    # model.weights = old_model.weights
                                    # model.voting = old_model.voting
                        model.fit(all_input, y.ravel())

            # manager_ns.total_portfolio = manager_ns.total_portfolio
            try:
                symbol_portfolio.sell_all(symbol, actual_prices[-1])
            except:
                print("error in sell ALL!!")
            symbol_portfolio.save_to_json(f"{trade_report_dir}/{symbol}_{interval}.json")

            # Plot the predicted prices and actual prices
            # plt.scatter(buy_x, buy_y, c='g', marker='^', label='Buy')
            # plt.scatter(sell_x, sell_y, c='r', marker='v', label='Sell')
            #
            # plt.plot(predicted_prices, label='Predicted')
            # plt.plot(actual_prices, label='Actual')
            # # Add a legend and show the plot
            # plt.legend()
            # plt.show()
            return symbol_portfolio


def run():
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(processSymbol, symbol,trade_report_dir) for symbol in symbols]
            protfolios = [result.result() for result in futures]
            total_portfolio = CryptoPortfolio.combine_portfolios(protfolios)
            # wait(futures)
        total_portfolio.save_to_json(f"{trade_report_dir}/total_portfolio.json")


if __name__ == '__main__':
    freeze_support()
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    trade_report_dir = f"{os.path.dirname(os.path.abspath(__file__))}/TradeReports/{current_time}"
    os.makedirs(trade_report_dir, exist_ok=True)
    run()



