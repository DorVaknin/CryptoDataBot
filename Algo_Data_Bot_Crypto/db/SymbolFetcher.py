from pymongo import MongoClient


class SymbolFetcher:
    def __init__(self,db_name):
        self.client = MongoClient()
        self.db = self.client[db_name]

    def fetch_all_symbols(self, interval):
        collection = self.db[interval]
        symbols = collection.distinct("symbol")
        return symbols

    def fetch_symbols_by_suffix(self, suffixes, interval):
        collection = self.db[interval]
        symbols = collection.distinct("symbol")
        symbols_filtered = []
        for symbol in symbols:
            for suffix in suffixes:
                if symbol.endswith(suffix):
                    symbols_filtered.append(symbol)
                    break
        symbols_filtered = list(set(symbols_filtered))
        return symbols_filtered

    def fetch_symbols_by_suffix_and_prefix(self, suffixes, interval):
        collection = self.db[interval]
        symbols = collection.distinct("symbol")
        symbols_filtered = []
        for symbol in symbols:
            for suffix in suffixes:
                if symbol.endswith(suffix):
                    prefix = symbol.rstrip(suffix)
                    if prefix not in symbols_filtered:
                        symbols_filtered.append(symbol)
                    break
        return symbols_filtered

    def fetch_symbol_by_usd_stable_coins(self,interval):
        return self.fetch_symbols_by_suffix_and_prefix(["USDT", "BUSD"], interval)
