import gridfs
import pymongo
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Connect to the MongoDB database
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["crypto"]

# Set the interval
interval = "1h"

# Query the collection for the specified interval to get the list of symbols
collection = db[interval]
# symbols = collection.distinct("symbol")

symbols = ["ETHBTC"]
# Create a new GridFS bucket for storing the models
model_bucket = gridfs.GridFSBucket(db, "models")

# Loop over the symbols
for symbol in symbols:
    # Query the collection for the specified interval and symbol
    klines = collection.find({"symbol": symbol})
    klines = list(klines)

    # Extract the timestamp, open, high, low, and close prices from the documents
    timestamps = [kline["timestamp"] for kline in klines]
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]

    # Combine the prices into a single feature matrix
    X = list(zip(opens, highs, lows, closes[:-1]))
    y = closes[1:]

    # Split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"fit the model for {symbol} for interval {interval} on train data")
    # Use the Random Forest Regressor to fit a model to the training data
    model = RandomForestRegressor()
    model.fit(X_train, y_train)

    print(f"calculate model score")
    # Evaluate the model's accuracy on the test data
    accuracy = model.score(X_test, y_test)

    print(f"fit the model for {symbol} for interval {interval} on all data")
    # Fit the model to the combined training and test data
    model.fit(X, y)

    # Serialize the model using pickle
    model_bytes = pickle.dumps(model)

    # Create a new document with the serialized model and accuracy score
    doc = {"symbol": symbol, "interval": interval, "score": accuracy}

    # Insert the model into the GridFS bucket
    model_id = model_bucket.upload_from_stream(symbol, model_bytes)

    print(f"insert the model for {symbol} for interval {interval} with score {accuracy}")
    # Update the document with the model's GridFS ID
    doc["model"] = model_id
    doc["latest_timestamp"] = timestamps[-1]
    model_collection = db["models"]
    model_collection.insert_one(doc)


