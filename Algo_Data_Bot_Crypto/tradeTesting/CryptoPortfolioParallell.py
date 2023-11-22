import json
from multiprocessing import Lock


class CryptoPortfolioParallell:
    def __init__(self):
        self.portfolio = {}
        self.portfolio_performance = 0
        self.initial_investment = 0
        self.fee_rate = 0.01
        self.portfolio_performance_percentage= 0
        self.profit_trades = 0
        self.loss_trades = 0
        self.lock = Lock()

    def set_fee_rate(self, fee_rate):
        self.fee_rate = fee_rate

    def add_buy_order(self, symbol, quantity, buy_price):
        with self.lock:
            if symbol in self.portfolio:
                self.portfolio[symbol]['quantity'] += quantity
                self.portfolio[symbol]['buy_price'] = (self.portfolio[symbol]['buy_price'] * self.portfolio[symbol][
                    'quantity'] + buy_price * quantity) / (self.portfolio[symbol]['quantity'] + quantity)
            else:
                self.portfolio[symbol] = {'quantity': quantity, 'buy_price': buy_price}
            self.initial_investment += buy_price*quantity*(1+self.fee_rate)
            print("Adding {} {} at {}. Portfolio value: {}".format(quantity, symbol, buy_price, self.portfolio_value()))

    def add_sell_order(self, symbol, quantity, sell_price):
        with self.lock:
            if symbol in self.portfolio:
                if self.portfolio[symbol]['quantity'] < quantity:
                    print("Error: Not enough quantity of {} to sell".format(symbol))
                    return
                else:
                    buy_price = self.portfolio[symbol]['buy_price']
                    trade_profit = (sell_price * quantity - buy_price * quantity) - (
                                sell_price * quantity + buy_price * quantity) * self.fee_rate
                    if trade_profit > 0:
                        self.profit_trades += 1
                    else:
                        self.loss_trades += 1
                    self.portfolio_performance += trade_profit
                    if self.portfolio[symbol]['quantity'] == quantity:
                        del self.portfolio[symbol]
                    else:
                        self.portfolio[symbol]['quantity'] -= quantity
                        self.portfolio[symbol]['buy_price'] = (self.portfolio[symbol]['buy_price'] * self.portfolio[symbol][
                            'quantity'] + sell_price * quantity) / (self.portfolio[symbol]['quantity'])
            else:
                print("Error: {} not in portfolio".format(symbol))
                return
            self.trade_performance()
            print("Closing order: Sold {} {} at {}. Portfolio value: {}".format(quantity, symbol, sell_price,
                                                                                self.portfolio_value()))


    def sell_all(self, symbol, sell_price):
        # with self.lock:
            if symbol in self.portfolio:
                self.add_sell_order(symbol, self.portfolio[symbol]['quantity'], sell_price)
            else:
                print("Error: {} not in portfolio".format(symbol))
                return

    def portfolio_value(self):
        # with self.lock:
            portfolio_value = self.portfolio_performance
            for symbol in self.portfolio:
                portfolio_value += self.portfolio[symbol]['buy_price'] * self.portfolio[symbol]['quantity']
            return portfolio_value

    def trade_performance(self):
        # with self.lock:
            if self.initial_investment == 0:
                return "No trade performance can be calculated as there is no trade yet"
            else:
                self.portfolio_performance_percentage = (
                                                               self.portfolio_performance / self.initial_investment) * 100 if self.portfolio_performance > 0 else (
                                                                                                                                                                              self.portfolio_performance / self.initial_investment) * 100
                return "Portfolio Performance: {} , Total Performance : {}%".format(self.portfolio_performance,
                                                                                    self.portfolio_performance_percentage)

    def save_to_json(self, file_name):
        delattr(self, 'lock')
        with open(file_name, 'w') as f:
            json.dump(self.__dict__, f)
        print("Portfolio saved to {}".format(file_name))
