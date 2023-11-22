import pandas as pd
from pymongo import MongoClient


class ModelFetcher:
    def __init__(self, db_name):
        self.client = MongoClient()
        self.db = self.client[db_name]

    def fetch_model(self, models_db_name,symbol, interval):
        collection = self.db[models_db_name]
        model = collection.find_one({"symbol": symbol,"interval" : interval})
        return model

    def fetch_models_dict(self, models_db_name,interval="1d"):
        collection = self.db[models_db_name]
        models = list(collection.find({"interval" : interval}))
        models_dict = {}
        for model in models:
            models_dict[model["symbol"]] = model
        return models_dict

