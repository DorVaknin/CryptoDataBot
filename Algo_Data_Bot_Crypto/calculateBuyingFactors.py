import numpy as np
import pandas as pd
import talib
from db.KlinesFetcher import KlinesFetcher
from db.SymbolFetcher import SymbolFetcher


def create_indicator_factory():
    indicator_factory = {
        'MA50': (talib.SMA, 50),
        'MA200': (talib.SMA, 200),
        'RSI': (talib.RSI, 14),
        'ADX': (talib.ADX, 14),
        'ATR': (talib.ATR, 14),
        'STOCHRSI': (talib.STOCHRSI, [14, 3, 3]),
        'MACD': (talib.MACD, [12, 26, 9])
    }
    return indicator_factory


def fetch_data():
    klines_fetcher = KlinesFetcher('crypto')
    symbol_fetcher = SymbolFetcher('crypto')
    df_symbols = list(symbol_fetcher.fetch_symbol_by_usd_stable_coins('1d'))
    return klines_fetcher, df_symbols


def calculate_indicators(df_token, indicator_factory):
    for indicator_name, (indicator_function, indicator_param) in indicator_factory.items():
        # Unpack the parameter if it exists, otherwise set it to None
        indicator_param = indicator_param if indicator_param else 14
        # Check if the indicator_param is exists
        if indicator_name == 'MA50':
            df_token[indicator_name] = indicator_function(df_token['close'], indicator_param)
        elif indicator_name == 'MA200':
            df_token[indicator_name] = indicator_function(df_token['close'], indicator_param)
        elif indicator_name == 'RSI':
            df_token[indicator_name] = indicator_function(df_token['close'], indicator_param)
        elif indicator_name == 'ADX':
            df_token[indicator_name] = indicator_function(df_token['high'], df_token['low'], df_token['close'],
                                                          timeperiod=indicator_param)
        elif indicator_name == 'ATR':
            df_token[indicator_name] = indicator_function(df_token['high'], df_token['low'], df_token['close'],
                                                          timeperiod=indicator_param)
        elif indicator_name == 'STOCHRSI':
            timeperiod1, fastd_period1, fastk_period1 = indicator_param
            df_token[indicator_name], fastd = talib.STOCHRSI(df_token["close"], timeperiod=timeperiod1,
                                                             fastk_period=fastk_period1, fastd_period=fastd_period1)
        elif indicator_name == 'MACD':
            fastperiod, slowperiod, signalperiod = indicator_param
            df_token[indicator_name], df_token['MACD_Signal'], macdhist = talib.MACD(df_token["close"],
                                                                                         fastperiod=fastperiod,
                                                                                         slowperiod=slowperiod,
                                                                                         signalperiod=signalperiod)

    return df_token


def determine_market_condition(df_token, index=-1):
    adx = df_token['ADX'].iloc[index]
    rsi = df_token['RSI'].iloc[index]
    stochrsi = df_token['STOCHRSI'].iloc[index]
    macd = df_token['MACD'].iloc[index]
    macd_signal = df_token['MACD_Signal'].iloc[index]
    if adx > 25 and rsi < 70 and stochrsi < 20:
        market_condition = 'trending'
    elif rsi > 70 and stochrsi > 80:
        market_condition = 'overbought'
    elif rsi < 30 and stochrsi < 20:
        market_condition = 'oversold'
    elif macd > macd_signal:
        market_condition = 'bullish'
    elif macd < macd_signal:
        market_condition = 'bearish'
    elif 50 < rsi < 70:
        market_condition = 'volatile'
    else:
        market_condition = 'ranging'

    return market_condition


def define_buy_sell_conditions(market_condition, df_token, index=-1):
    if market_condition == 'trending':
        buy_conditions = [df_token['MA50'].iloc[index] > df_token['MA200'].iloc[index],
                          df_token['RSI'].iloc[index] < 70,
                          df_token['STOCHRSI'].iloc[index] < 20,
                          ]
        sell_conditions = [df_token['MA50'].iloc[index] < df_token['MA200'].iloc[index],
                           df_token['RSI'].iloc[index] > 70,
                           df_token['STOCHRSI'].iloc[index] > 80,
                           ]
    elif market_condition == 'overbought':
        buy_conditions = []
        sell_conditions = [df_token['RSI'].iloc[index] > 70,
                           df_token['STOCHRSI'].iloc[index] > 80,
                           ]
    elif market_condition == 'oversold':
        buy_conditions = [df_token['RSI'].iloc[index] < 30,
                          ]
        sell_conditions = []
    elif market_condition == 'bullish':
        buy_conditions = [df_token['MACD'].iloc[index] > df_token['MACD_Signal'].iloc[index],
                          ]
        sell_conditions = [df_token['MACD'].iloc[index] < df_token['MACD_Signal'].iloc[index],
                           ]
    elif market_condition == 'bearish':
        buy_conditions = []
        sell_conditions = [df_token['MACD'].iloc[index] < df_token['MACD_Signal'].iloc[index],
                           ]
    elif market_condition == 'volatile':
        buy_conditions = [df_token['RSI'].iloc[index] < 50,
                          ]
        sell_conditions = [df_token['RSI'].iloc[index] > 50,
                           ]
    else:
        buy_conditions = [df_token['RSI'].iloc[index] < 30,
                          ]
        sell_conditions = [df_token['RSI'].iloc[index] > 70,
                           ]
    return buy_conditions, sell_conditions


def execute_order(buy_conditions, sell_conditions, holding, token, current_token_list):
    if all(buy_conditions) and not holding:
        # Execute buy order for the token
        holding = True
        print(f'Buying {token}...')
        current_token_list.append(token)
    elif all(sell_conditions) and holding:
        # Execute sell order for the token
        holding = False
        print(f'Selling {token}...')
        current_token_list.remove(token)
    return holding, current_token_list


def main():
    klines_fetcher, df_symbols = fetch_data()
    indicator_factory = create_indicator_factory()

    for symbol in df_symbols:
        df_token = klines_fetcher.fetch_klines_df(symbol, '1d')
        df_token = calculate_indicators(df_token, indicator_factory)
        market_condition = determine_market_condition(df_token)
        buy_conditions, sell_conditions = define_buy_sell_conditions(market_condition, df_token)
        holding = False
        current_token_list = []
        execute_order(buy_conditions, sell_conditions, holding, symbol, current_token_list)


if __name__ == '__main__':
    main()
