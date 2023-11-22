import requests
import pymongo
import pandas as pd
import time

# Connect to the MongoDB server

client = pymongo.MongoClient()

# Select the database
db = client['crypto']

# Set the URL for the API endpoint
url = 'https://api.binance.com/api/v3/exchangeInfo'

# Send the request and get the response
response = requests.get(url)

# Convert the response to a dictionary
data = response.json()

# Get the list of symbols
symbols = [d['symbol'] for d in data['symbols']]

# Set the intervals
intervals = ['1d']

# Set the base URL for the API endpoint
base_url = 'https://api.binance.com/api/v3/klines'

# Set the parameters for the API endpoint
params = {
    'interval': '1h'
}

# Set the maximum number of candles to return
params['limit'] = 1000

# Set the start and end dates for the data
start_date = '2017-01-01 00:00:00'
end_date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

# Convert the dates to timestamps
start_timestamp = pd.Timestamp(start_date).timestamp() * 1000
end_timestamp = pd.Timestamp(end_date).timestamp() * 1000
end_timestamp = 1673049600000
startFromSymbol = 0
check_mongo = True
print(f'all {len(symbols)} symbols form binance : {symbols}')
symbols = symbols[startFromSymbol:]
# Iterate over the symbols
for indx,symbol in enumerate(symbols):
    print(f'featching symbol {indx}/{len(symbols)}')
    # Iterate over the intervals
    for interval in intervals:
        print(f'featching symbol {symbol} and interval {interval}')
        # Select the collection for the interval
        collection = db[interval]

        if check_mongo:
            try:
                max_timestamp = collection.find({'symbol': symbol}).sort('timestamp', pymongo.DESCENDING).limit(1)[0][
                    'timestamp']
            except:
                max_timestamp = None
                check_mongo = False

        if max_timestamp:
            print(f'timestamp found starting from {max_timestamp}')
            start = max_timestamp
        else:
            # Set the initial start timestamp
            start = start_timestamp

        while start < end_timestamp:
            # Set the interval and symbol parameters
            params['interval'] = interval
            params['symbol'] = symbol

            # Set the start and end timestamps
            params['startTime'] = int(start)
            params['endTime'] = int(end_timestamp)

            # Send the request and get the response
            response = requests.get(base_url, params=params)

            # Check the status code of the response
            if response.status_code == 200:
                # Convert the response to a dictionary
                data = response.json()

                # Convert the data to a DataFrame
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignored'])

                # Set the timestamp column as the index
                df.set_index('timestamp',drop=False, inplace=True)

                # Convert the timestamp column to a datetime
                df.index = pd.to_datetime(df.index, unit='ms')

                # Add the interval and symbol to the data
                df['interval'] = interval
                df['symbol'] = symbol

                # Insert the data into the collection
                collection.insert_many(df.to_dict('records'))
                # Check if the data array is less than the limit
                if len(data) < params['limit']:
                    # Break out of the loop
                    break
                # Update the start timestamp
                start = df.index[-1].timestamp() * 1000
            elif response.status_code == 429:
                print(f'retry headers: {response.headers}')
                # Get the retry-after header
                retry_after = response.headers['Retry-After']

                # Sleep for the specified number of seconds
                time.sleep(int(retry_after))
            else:
                # Print the status code and message
                print(response.status_code, response.reason)

