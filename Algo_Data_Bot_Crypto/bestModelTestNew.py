# Preprocess the input data
import pickle

import gridfs
import pymongo
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]

# Set the interval
interval = "1h"

# Query the collection for the specified interval to get the list of symbols
collection = db[interval]
# symbols = collection.distinct("symbol")

symbols = ["BTCUSDT"]
# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")

# Standardize the data
scaler = StandardScaler()

# Loop over the symbols
for symbol in symbols:
    # Query the collection for the specified interval and symbol
    klines = collection.find({"symbol": symbol})
    klines = list(klines)

    # Extract the open, high, low, and close prices from the documents
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]
    # Combine the prices into a single feature matrix
    X = list(zip(opens, highs, lows, closes[:-1],volumes[:-1]))
    y = closes[1:]


    X = scaler.fit_transform(X)
    scaler.fit_transform(y)
    # Serialize the StandardScaler object
    scaler_bytes = pickle.dumps(scaler)
    # Split the data into training and test sets
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Try different models
    from sklearn.linear_model import LinearRegression
    from sklearn.svm import SVR
    from sklearn.neural_network import MLPRegressor

    models = [LinearRegression(), SVR(), MLPRegressor(),RandomForestRegressor()]
    best_model = None
    best_score = float("-inf")

    for model in models:
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        if score > best_score:
            best_score = score
            best_model = model

    # Fit the model to the combined training and test data
    best_model.fit(X, y)

    # Tune the hyperparameters of the best model using grid search
    # from sklearn.model_selection import GridSearchCV
    #
    # if isinstance(best_model, LinearRegression):
    #     # Use different hyperparameters for linear regression
    #     param_grid = {"fit_intercept": [True, False]}
    # else:
    #     # Use different hyperparameters for other models
    #     param_grid = {"C": [0.1, 1, 10], "gamma": [0.1, 1, 10]}
    # grid_search = GridSearchCV(best_model, param_grid, cv=5)
    # grid_search.fit(X, y)
    # best_model = grid_search.best_estimator_

    # Serialize the model using pickle
    model_bytes = pickle.dumps(best_model)

    # Create a new document with the serialized model and accuracy score
    doc = {"symbol": symbol, "interval": interval}

    # Insert the model into the GridFS bucket
    model_id = model_bucket.upload_from_stream(symbol, model_bytes)

    print(f"insert the model for {symbol} for interval {interval} with score")
    # Update the document with the model's GridFS ID
    doc["model"] = model_id
    doc["scaler_x"] =scaler_bytes
    doc["latest_timestamp"] = klines[-1]["timestamp"]
    model_collection = db["models"]
    model_collection.insert_one(doc)




    # # Use cross-validation to get a more accurate estimate of the model's generalization error
    # from sklearn.model_selection import cross_val_score
    # scores = cross_val_score(best_model, X, y, cv=5)
    #
    # # Consider using an ensemble of models
    # from sklearn.ensemble import RandomForestRegressor
    # from sklearn.ensemble import GradientBoostingRegressor
    #
    # ensemble = RandomForestRegressor()
    # ensemble.fit(X_train, y_train)
    # ensemble_scores = cross_val_score(ensemble, X, y, cv=5)
    #
    # ensemble = GradientBoostingRegressor()
    # ensemble.fit(X_train, y_train)
    # ensemble_scores = cross_val_score(ensemble, X, y, cv=5)
