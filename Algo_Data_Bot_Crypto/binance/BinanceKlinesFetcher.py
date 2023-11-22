import requests
import pandas as pd


class BinanceKlinesFetcher:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3/klines"

    def fetch_klines(self, symbol, interval, start=None, end=None,exclude_start=True, exclude_end=True, as_df=True):
        params = {
            'interval': interval,
            'limit': 1000,
            'symbol': symbol
        }
        if start is not None:
            params['startTime'] = int(start)
        if end is not None:
            params['endTime'] = int(end)

        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if exclude_end:
                data = data[:-1]
            if exclude_start:
                data = data[1:]
            if as_df:
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                                 'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume',
                                                 'taker_buy_quote_asset_volume', 'ignored'])
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(
                    float)
                return df
            else:
                for i in range(len(data)):
                    data[i][1], data[i][2], data[i][3], data[i][4], data[i][5] = float(data[i][1]), float(
                        data[i][2]), float(data[i][3]), float(data[i][4]), float(data[i][5])
                return data
        else:
            return None
