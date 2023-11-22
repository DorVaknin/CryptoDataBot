# Preprocess the input data
import pickle

import gridfs
import numpy as np
import pymongo
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]

# Set the interval
interval = "1h"

# Query the collection for the specified interval to get the list of symbols
collection = db[interval]
# symbols = collection.distinct("symbol")

symbols = ["ETHUSDT"]
# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")


scaler = StandardScaler()
X_all, y_all = [], []
for symbol in symbols:
    # Query the collection for the specified interval and symbol
    klines = collection.find({"symbol": symbol})
    klines = list(klines)
    # klines = klines[len(klines)-8760:len(klines)]
    # Extract the open, high, low, and close prices from the documents
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]
    # Combine the prices into a single feature matrix
    X = list(zip(opens[:-1], highs[:-1], lows[:-1], closes[:-1],volumes[:-1]))
    y = closes[1:]

    # concatenate all the data
    # X_all = np.concatenate(X)
    # y_all = np.concatenate(y)
    # reshaping y_all to have 2 dimensions
    # y_all = y.reshape(-1,X.shape[1])
    y = np.array(y)
    y = y.reshape(-1, 1)
    # Fit the scaler_x on all the data
    data = np.concatenate([X, y], axis=1)
    scaler.fit(data)

    # Transform all the data
    data = scaler.transform(data)

    # Split the data into X and y
    X = data[:, :-1]
    y = data[:, -1]
    # Serialize the StandardScaler object
    scaler_bytes = pickle.dumps(scaler)
    # Split the data into training and test sets
    from sklearn.model_selection import train_test_split, cross_val_score

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Try different models
    from sklearn.linear_model import LinearRegression
    from sklearn.svm import SVR
    from sklearn.neural_network import MLPRegressor

    models = [ SVR(), MLPRegressor(),RandomForestRegressor()]
    best_model = None
    best_score = float("-inf")

    for model in models:
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        if score > best_score:
            best_score = score
            best_model = model



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

    from sklearn.metrics import mean_absolute_percentage_error
    from sklearn.ensemble import VotingRegressor


    # define a function to calculate the MAPE
    def mape(y_true, y_pred, sample_weight=None):
        y_true = np.squeeze(y_true)
        y_pred = np.squeeze(y_pred)
        if sample_weight is not None:
            return np.average(np.abs((y_true - y_pred) / y_true), weights=sample_weight)
        else:
            return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


    # Get the mean cross-validation score for each model using R2 and MAPE
    best_model_score_r2 = np.mean(cross_val_score(best_model, X, y, cv=5, scoring='r2'))
    best_model_score_mape = np.mean(cross_val_score(best_model, X, y, cv=5, scoring=mape))
    rf_score_r2 = np.mean(cross_val_score(RandomForestRegressor(), X, y, cv=5, scoring='r2'))
    rf_score_mape = np.mean(cross_val_score(RandomForestRegressor(), X, y, cv=5, scoring=mape))
    gb_score_r2 = np.mean(cross_val_score(GradientBoostingRegressor(), X, y, cv=5, scoring='r2'))
    gb_score_mape = np.mean(cross_val_score(GradientBoostingRegressor(), X, y, cv=5, scoring=mape))
    ensemble = VotingRegressor(
        [('best_model', best_model), ('rf', RandomForestRegressor()), ('gb', GradientBoostingRegressor())])
    ensemble_score_r2 = np.mean(cross_val_score(ensemble, X, y, cv=5, scoring='r2'))
    ensemble_score_mape = np.mean(cross_val_score(ensemble, X, y, cv=5, scoring=mape))

    # Print the scores
    print("Best Model R-squared: ", best_model_score_r2)
    print("Best Model MAPE: ", best_model_score_mape)
    print("Random Forest R-squared: ", rf_score_r2)
    print("Random Forest MAPE: ", rf_score_mape)
    print("Gradient Boosting R-squared: ", gb_score_r2)
    print("Gradient Boosting MAPE: ", gb_score_mape)
    print("Ensemble R-squared: ", ensemble_score_r2)
    print("Ensemble MAPE: ", ensemble_score_mape)

    # Compare the scores and select the best model
    if ensemble_score_r2 > best_model_score_r2 and ensemble_score_mape < best_model_score_mape:
        best_model = ensemble
        print("Ensemble is the best")
    elif best_model_score_r2 > rf_score_r2 and best_model_score_mape < rf_score_mape:
        print("Best Model is the best")
    elif rf_score_r2 > best_model_score_r2 and rf_score_mape < best_model_score_mape:
        best_model = RandomForestRegressor()
        print("Random Forest is the best")
    elif gb_score_r2 > best_model_score_r2 and gb_score_mape < best_model_score_mape:
        best_model = GradientBoostingRegressor()
        print("Gradient Boosting is the best")

    # Re-fit the best model on the full dataset
    best_model.fit(X, y)

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
    input("Press Enter to exit...")