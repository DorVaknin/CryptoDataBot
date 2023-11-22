# Preprocessing the data
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def calculate_accuracy(test,predictions, target):
    """Calculate the accuracy of the model's predictions.

    Args:
        predictions: A list of predictions made by the model.
        target: A list of the target values.

    Returns:
        The accuracy of the model's predictions, as a float between 0 and 1.
    """
    correct = 0
    for i in range(len(predictions)):
        if predictions[i] == target[i]:
            correct += 1
    return correct / len(predictions)
import time
from binance.spot import Spot

# Set the interval and quantity for trading
INTERVAL = 60  # seconds
QUANTITY = 0.001  # BTC

# Set the threshold for the accuracy of the model
THRESHOLD = 0.7

# Set the endpoint for the Binance Spot Test Network
endpoint = 'https://testnet.binance.vision'

# Create a Binance client using the Binance Public API Connector Python library
client = Spot(key=API_KEY, secret=API_SECRET, base_url=endpoint)

# Fetch data for the specified symbol and time interval
symbol = 'BTCUSDT'
interval = '1h'
klines = client.klines(symbol=symbol, interval=interval, limit=500000)

# Convert the raw data into a Pandas DataFrame
columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored']
df = pd.DataFrame(klines, columns=columns)

# Preprocessing the data
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)
df.drop(['close_time', 'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'], axis=1, inplace=True)
df = df.astype(float)

# Split the data into train and test sets
split_index = int(len(df) * 0.8)
train_df = df[:split_index]
test_df = df[split_index:]

# Build and train the model
from sklearn.ensemble import RandomForestRegressor

# Set the target column
target_column = 'close'

# Split the data into features and target
X = train_df.drop(target_column, axis=1)
y = train_df[target_column]

model = RandomForestRegressor()
model.fit(X, y)

# Split the test data into features and target
X_test = test_df.drop(target_column, axis=1)
y_test = test_df[target_column]
# Run the model on the test data and calculate accuracy
predictions = model.predict(X_test)
accuracy = calculate_accuracy(X_test,predictions, y_test)

# If the accuracy is above the threshold, execute trades
if accuracy > THRESHOLD:
    while True:
        # Get the current price of the symbol
        ticker = client.ticker(symbol=symbol)
        current_price = float(ticker['lastPrice'])

        # Use the model to make a prediction about the next price
        prediction = model.predict(current_price)

        # If the prediction is positive, place a buy order
        if prediction > 0:
            response = client.new_order(symbol=symbol, side='BUY', type='MARKET', quantity=QUANTITY)
            print(response)

        # If the prediction is negative, place a sell order
        elif prediction < 0:
            response = client.new_order(symbol=symbol, side='SELL', type='MARKET', quantity=QUANTITY)
            print(response)

        # Sleep for the specified interval before making the next prediction
        time.sleep(INTERVAL)

else:
    print(f'Accuracy not above threshold ({accuracy:.2f} < {THRESHOLD:.2f})')
