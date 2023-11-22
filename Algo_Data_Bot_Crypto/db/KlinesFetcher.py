import pandas as pd
from pymongo import MongoClient

class KlinesFetcher:
    def __init__(self, db_name):
        self.client = MongoClient()
        self.db = self.client[db_name]

    def fetch_klines_list(self, symbol, interval, max_timestamp=None):
        collection = self.db[interval]
        query = {"symbol": symbol}
        if max_timestamp is not None:
            query["timestamp"] = {"$lt": max_timestamp}
        klines = list(collection.find(query))
        for kline in klines:
            kline["open"] = float(kline["open"])
            kline["high"] = float(kline["high"])
            kline["low"] = float(kline["low"])
            kline["close"] = float(kline["close"])
            kline["volume"] = float(kline["volume"])
        return klines

    def fetch_klines_df(self, symbol, interval, max_timestamp=None):
        klines = self.fetch_klines_list(symbol, interval, max_timestamp)
        klines_df = pd.DataFrame(klines)
        return klines_df
