from calculateBuyingFactors import calculate_indicators, determine_market_condition, create_indicator_factory, \
    define_buy_sell_conditions, fetch_data
import os
from multiprocessing import freeze_support
from datetime import datetime
from tradeTesting.CryptoPortfolioLimitedCash import CryptoPortfolioLimitedCash as CryptoPortfolio
import matplotlib.pyplot as plt
from concurrent.futures import wait, ProcessPoolExecutor

total_portfolio = CryptoPortfolio()
DAY_TO_START_FROM = 201


def process_symbol(df_token, trade_report_dir):
    buy_x, buy_y, sell_x, sell_y = [], [], [], []
    token_portfolio = CryptoPortfolio()
    symbol_name = df_token['symbol'][0]
    holding = False
    df_token = calculate_indicators(df_token, create_indicator_factory())
    for i in range(DAY_TO_START_FROM, len(df_token)):
        market_condition = determine_market_condition(df_token, index=i)
        buy_conditions, sell_conditions = define_buy_sell_conditions(market_condition, df_token, index=i)
        holding = check_buy_conditions(df_token, token_portfolio, symbol_name, i, buy_conditions, buy_x, buy_y) or holding
        holding = check_sell_conditions(df_token, token_portfolio, symbol_name, i, sell_conditions, sell_x, sell_y, holding) or holding

    show_plot_and_save_json(df_token, buy_x, buy_y, sell_x, sell_y, symbol_name, trade_report_dir, token_portfolio)

    return token_portfolio


def check_buy_conditions(df_token, token_portfolio, symbol_name, index, buy_conditions, buy_x, buy_y):
    if all(c == True for c in buy_conditions):
        token_portfolio.add_buy_order(symbol_name, df_token['close'][index])
        buy_x.append(index)
        buy_y.append(df_token['close'][index])
        holding = True
        return holding


def check_sell_conditions(df_token, token_portfolio, symbol_name, index, sell_conditions, sell_x, sell_y, holding):
    print(f"sellConditions2: {sell_conditions}")
    if all(c == True for c in sell_conditions) and holding:
        token_portfolio.sell_all(symbol_name, df_token['close'][index])
        sell_x.append(index)
        sell_y.append(df_token['close'][index])
        holding = False
        return holding


def show_plot(df_token, buy_x, buy_y, sell_x, sell_y):
    plt.scatter(buy_x, buy_y, c='g', marker='^', label='Buy')
    plt.scatter(sell_x, sell_y, c='r', marker='v', label='Sell')
    plt.plot(df_token['close'][DAY_TO_START_FROM:], label='Actual')
    plt.legend()
    plt.show()


def save_json(symbol_name, trade_report_dir, token_portfolio):
    token_portfolio.save_to_json(f"{trade_report_dir}/{symbol_name}.json")


def show_plot_and_save_json(df_token, buy_x, buy_y, sell_x, sell_y, symbol_name, trade_report_dir, token_portfolio):
    save_json(symbol_name, trade_report_dir, token_portfolio)
    show_plot(df_token, buy_x, buy_y, sell_x, sell_y)


def run(trade_report_dir):
    klines_fetcher, df_symbols = fetch_data()
    minimized_symbol_list = df_symbols[-10:]
    symbols = ["SOLBUSD"]
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_symbol, klines_fetcher.fetch_klines_df(symbol, interval='1d'), trade_report_dir) for symbol in
                   minimized_symbol_list]
        portfolios = [result.result() for result in futures]
        total_portfolio = CryptoPortfolio.combine_portfolios(portfolios)
        wait(futures)
    total_portfolio.save_to_json(f"{trade_report_dir}/total_portfolio.json")


if __name__ == '__main__':
    freeze_support()
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    trade_report_dir = f"{os.path.dirname(os.path.abspath(__file__))}/TradeReports/{current_time}"
    os.makedirs(trade_report_dir, exist_ok=True)
    run(trade_report_dir)
