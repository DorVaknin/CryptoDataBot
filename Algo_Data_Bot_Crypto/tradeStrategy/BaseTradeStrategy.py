
import pandas as pd


class BaseTradeStrategy:
    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        if old_predicted_price < predicted_price:
            portfolio.add_buy_order(symbol, (usd_per_symbol / actual_price), actual_price)

    def sell_strategy(self,klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price):
        if old_predicted_price > predicted_price:
            portfolio.sell_all(symbol, actual_price)


class TradeStratagyAboveThreshold(BaseTradeStrategy):
    def __init__(self, threshold):
        self.threshold = threshold

    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        change_in_percent = ((predicted_price - old_predicted_price) / old_predicted_price) * 100
        if change_in_percent > self.threshold:
            portfolio.add_buy_order(symbol, (usd_per_symbol / actual_price), actual_price)


class TradeStratagyWithIndicators(BaseTradeStrategy):
    def __init__(self, threshold):
        self.threshold = threshold
    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        change_in_percent = ((predicted_price - old_predicted_price) / old_predicted_price) * 100
        if change_in_percent >= self.threshold and check_technical_indicator(klines):
            portfolio.add_buy_order(symbol, usd_per_symbol / actual_price, actual_price)

    def sell_strategy(self,klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price):
        if old_predicted_price > predicted_price and check_technical_indicator_RSI(klines) and not check_technical_indicator(klines):
            portfolio.sell_all(symbol, actual_price)


class TradeStrategyDropThreshold(BaseTradeStrategy):
    def __init__(self, buy_threshold, sell_threshold):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.original_price = {}

    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        change_in_percent = ((predicted_price - old_predicted_price) / old_predicted_price) * 100
        if change_in_percent > self.buy_threshold:
            portfolio.add_buy_order(symbol, (usd_per_symbol / actual_price), actual_price)
            if symbol not in self.original_price:
                self.original_price[symbol] = old_predicted_price

    def sell_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price):
        if symbol in self.original_price:
            drop = ((self.original_price[symbol] - predicted_price) / self.original_price[symbol]) * 100
            if drop > self.sell_threshold:
                portfolio.sell_all(symbol, actual_price)
                del self.original_price[symbol]


class TradeStrategySellWithIndicators(BaseTradeStrategy):
    def __init__(self):
        self.bought_symbols = set()

    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        if old_predicted_price < predicted_price and symbol not in self.bought_symbols:
            portfolio.add_buy_order(symbol, (usd_per_symbol / actual_price), actual_price)
            self.bought_symbols.add(symbol)

    def sell_strategy(self,klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price):
        if old_predicted_price > predicted_price and check_technical_indicator_RSI(klines) and not check_technical_indicator(klines):
            portfolio.sell_all(symbol, actual_price)
            if symbol in self.bought_symbols :
                self.bought_symbols.remove(symbol)

class TradeStrategySellWithIndicatorsWithThreshold(BaseTradeStrategy):
    def __init__(self,threshold):
        self.threshold = threshold
        self.bought_symbols = set()

    def buy_strategy(self, klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price,
                     usd_per_symbol):
        change_in_percent = ((predicted_price - old_predicted_price) / old_predicted_price) * 100
        if change_in_percent >= self.threshold and check_technical_indicator(klines) and symbol not in self.bought_symbols:
            portfolio.add_buy_order(symbol, usd_per_symbol / actual_price, actual_price)
            self.bought_symbols.add(symbol)

    def sell_strategy(self,klines, portfolio, symbol, predicted_price, old_predicted_price, actual_price):
        if old_predicted_price > predicted_price and check_technical_indicator_RSI(klines) and not check_technical_indicator(klines):
            portfolio.sell_all(symbol, actual_price)
            if symbol in self.bought_symbols :
                self.bought_symbols.remove(symbol)

def check_technical_indicator(klines):
    timestamps = [kline["timestamp"] for kline in klines]
    opens = [float(kline["open"]) for kline in klines]
    highs = [float(kline["high"]) for kline in klines]
    lows = [float(kline["low"]) for kline in klines]
    closes = [float(kline["close"]) for kline in klines]
    volumes = [float(kline["volume"]) for kline in klines]

    # Define the parameters of the moving averages
    short_window = 12
    long_window = 26
    signal_window = 9

    short_moving_average = moving_average(closes[-min(short_window, len(closes)):], short_window)
    long_moving_average = moving_average(closes[-min(long_window, len(closes)):], long_window)


    # Compute the MACD
    macd = short_moving_average - long_moving_average
    signal = moving_average(macd, signal_window)
    histogram = macd - signal
    if histogram[-1] > 0:
        return True
    else:
        return False

def check_technical_indicator_RSI(klines, window=14, oversold=30, overbought=70):
    closes = [float(kline["close"]) for kline in klines]
    up_gain = [closes[i] - closes[i-1] if closes[i] > closes[i-1] else 0 for i in range(1, len(closes))]
    down_loss = [-closes[i] + closes[i-1] if closes[i] < closes[i-1] else 0 for i in range(1, len(closes))]
    avg_gain = np.mean(up_gain[-window:])
    avg_loss = np.mean(down_loss[-window:])
    if avg_loss == 0:
        return False
    else:
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss)))
    if rsi < oversold:
        return True # it's oversold
    if rsi > overbought:
        return True # it's overbought
    return False

import numpy as np


def moving_average(values, window):
    weights = np.repeat(1.0, window) / window
    smas = np.convolve(values, weights, 'valid')
    return smas
