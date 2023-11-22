# Preprocessing the data
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def calculate_accuracy(predictions, target):
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

# Set your API key and secret here
API_KEY = 'jiyObKu8LtFl3XE8PNzmy7AdFDwsJlrJQtkh2Nt8VkYN83GncCiuxumfFgbfS7fY'
API_SECRET = 'TucG5pn9b95Mguw9RDXX1idTiqj8nchT0V5oqKR9V0Iqsks7S6f8pe9sInAOgdy8'

# Set the interval and quantity for trading
INTERVAL = 60  # seconds
QUANTITY = 0.001  # BTC

# Set the threshold for the accuracy of the model
THRESHOLD = 0.7

import requests
import pandas as pd

# Set the symbol, the start and end timestamps, and the interval
symbol = 'BTC'
start = '2022-01-01'
end = '2022-01-31'
interval = '1h'

# Set the URL for the API endpoint
url = f'https://min-api.cryptocompare.com/data/histohour?fsym={symbol}&tsym=USD&limit=2000&toTs={end}&aggregate=1&e=CCCAGG'

# Send the request and get the response
response = requests.get(url)

# Convert the response to a dictionary
data = response.json()

# Convert the dictionary to a DataFrame
df = pd.DataFrame(data['Data'])

# Convert the timestamp column to a datetime and set it as the index
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

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
accuracy = calculate_accuracy(predictions, y_test)

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
