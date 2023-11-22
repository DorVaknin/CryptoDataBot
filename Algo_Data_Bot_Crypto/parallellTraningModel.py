import pickle
import re
from datetime import timedelta
from multiprocessing import freeze_support, set_start_method

import gridfs
import numpy as np
import pymongo
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from concurrent.futures import ProcessPoolExecutor




# Connect to the MongoDB database
from sklearn.svm import SVR

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]

# Set the interval
interval = "1d"
# Define the window size
default_window_size = 10
# Query the collection for the specified interval to get the list of symbols
collection = db[interval]

db_models_name = "models_until_2023_dynamic_window_size"
# symbols = ["SOLBUSD"]
model_collection = db[db_models_name]

dynamic_window_size = True
max_timestamp = None

symbols = collection.distinct("symbol")
# TODO add and check USDC in binance symbols
pattern = '(BUSD|USDT)$'
symbols = [s for s in symbols if re.search(pattern, s)]
# symbols_count = {}
# # for symbol in symbols:
# #     base_symbol = re.sub(pattern, '', symbol)
# #     if base_symbol in symbols_count:
# #         symbols_count[base_symbol].append(symbol)
# #     else:
# #         symbols_count[base_symbol] = [symbol]
# # filter duplicate symbols
# symbols = [symbols_count[base_symbol][0] for base_symbol in symbols_count if len(symbols_count[base_symbol]) > 0]



# Create a new GridFS bucket  for storing the models
model_bucket = gridfs.GridFSBucket(db, db_models_name)

import numpy as np


def determine_window_size(closes, window_size_factor=0.1):
    # Calculate volatility of the symbol
    volatility = np.std(closes)

    # if volatility is high, use a higher window size factor
    if volatility > 0.1:
        window_size_factor = 0.2
    # Determine the window size based on the volatility and the window size factor
    window_size = round(volatility * window_size_factor)

    window_size = max(window_size,1)

    return window_size


def train_model(symbol):
    print(f"start training on {symbol}")
    # Query the collection for the specified interval and symbol

    if max_timestamp:
        klines = collection.find({"symbol": symbol, "timestamp": {"$lt": max_timestamp}})
    else:
        klines = collection.find({"symbol": symbol})
    klines = list(klines)
    if klines:

        # Extract the open, high, low, and close prices from the documents
        opens = [float(kline["open"]) for kline in klines]
        highs = [float(kline["high"]) for kline in klines]
        lows = [float(kline["low"]) for kline in klines]
        closes = [float(kline["close"]) for kline in klines]
        volumes = [float(kline["volume"]) for kline in klines]

        if dynamic_window_size:
            window_size = determine_window_size(closes)
        else:
            window_size = default_window_size

        print(f"window size is {window_size}")
        X_y = []

        X,y = [],[]
        scaler_x = StandardScaler()
        scaler_y = StandardScaler()
        for i in range(len(closes) - window_size):
            X.append(np.hstack((opens[i:i + window_size], highs[i:i + window_size], lows[i:i + window_size],
                                closes[i:i + window_size], volumes[i:i + window_size])))

            y.append(closes[i + window_size])

        y = np.array(y)
        y = y.reshape(-1, 1)
        scaler_x.fit(X)
        scaler_y.fit(y)

        X = scaler_x.transform(X)
        y = scaler_y.transform(y)
        scaler_x_bytes = pickle.dumps(scaler_x)
        scaler_y_bytes = pickle.dumps(scaler_y)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        y = y.ravel()
        y_train = y_train.ravel()
        y_test = y_test.ravel()

        models = [SVR(), MLPRegressor(), RandomForestRegressor(),
                  VotingRegressor(
                      [('rf', RandomForestRegressor()), ('gb', GradientBoostingRegressor())])
                  ]
        best_model = None
        best_score = float("-inf")
        with ProcessPoolExecutor() as model_executor:
            model_results = [model_executor.submit(train_models, model, X_train, y_train) for model in models]
            model_best_scores = [result.result() for result in model_results]
        for model, score in zip(models, model_best_scores):
            if score.mean() > best_score:
                best_score = score.mean()
                best_model = model

        # TODO check if we need to fit all the data on the best model maybe a bug ?
        best_model.fit(X, y)
        print(f"finish training on {symbol}")
        saveModelToDB(symbol, best_model, best_score,klines[-1]["timestamp"],scaler_x_bytes,scaler_y_bytes,window_size)
        return [best_model,best_score]


def train_models(model, X_train, y_train):
    scores = cross_val_score(model, X_train, y_train, cv=5)
    return scores



def run():
    with ProcessPoolExecutor() as symbol_executor:
        symbol_results = [symbol_executor.submit(train_model, symbol) for symbol in symbols]
        symbol_best_models = [result.result() for result in symbol_results]

    # symbol_best_models = [train_model(symbol,window_size) for symbol in symbols]
    # for symbol, (best_model, best_score) in zip(symbols, symbol_best_models):
    #     saveModelToDB(symbol, best_model, best_score)
    input("Press enter to exit...")


def saveModelToDB(symbol, best_model, best_score,last_timestamp,scaler_x,scaler_y,window_size):
    # Serialize the model
    model_bytes = pickle.dumps(best_model)
    # check if model already exists
    existing_model = model_collection.find_one({"symbol": symbol, "interval": interval})
    if existing_model is not None:
        model_id = existing_model.get('model_id') or existing_model.get('model')
        if model_id is not None:
            # delete the existing model
            model_bucket.delete(model_id)
    # Write the model to the GridFS bucket
    model_id = model_bucket.upload_from_stream(f'{symbol}_{interval}.pkl', model_bytes)
    # Update the models collection with the new model
    model_collection.update_one({"symbol": symbol, "interval": interval},
                         {"$set": {"scaler_x": scaler_x,"scaler_y": scaler_y,"model_id": model_id, "score": best_score, "window_size": window_size,"latest_timestamp": last_timestamp}}, upsert=True)
    print(f"Successfully trained and saved model for {symbol}")




if __name__ == '__main__':
    freeze_support()
    run()