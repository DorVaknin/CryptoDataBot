# import json
#
#
# class CryptoPortfolio:
#     def __init__(self):
#         self.portfolio = {}
#         self.portfolio_performance = 0
#         self.initial_investment = 0
#         self.cash_balance = 0
#         self.fee_rate = 0.01
#         self.portfolio_performance_percentage = 0
#         self.profit_trades = 0
#         self.loss_trades = 0
#
#     def set_fee_rate(self, fee_rate):
#         self.fee_rate = fee_rate
#
#     def add_buy_order(self, symbol, quantity, buy_price):
#         if symbol in self.portfolio:
#             self.portfolio[symbol]['quantity'] += quantity
#             self.portfolio[symbol]['buy_price'] = (self.portfolio[symbol]['buy_price'] * self.portfolio[symbol][
#                 'quantity'] + buy_price * quantity) / (self.portfolio[symbol]['quantity'] + quantity)
#         else:
#             self.portfolio[symbol] = {'quantity': quantity, 'buy_price': buy_price}
#         self.cash_balance -= buy_price * quantity * (1 + self.fee_rate)
#         print("Adding {} {} at {}. Portfolio value: {}".format(quantity, symbol, buy_price, self.portfolio_value()))
#
#     def add_sell_order(self, symbol, quantity, sell_price):
#         if symbol in self.portfolio:
#             if self.portfolio[symbol]['quantity'] < quantity:
#                 print("Error: Not enough quantity of {} to sell".format(symbol))
#                 return
#             else:
#                 buy_price = self.portfolio[symbol]['buy_price']
#                 trade_profit = (sell_price * quantity - buy_price * quantity) - (
#                         sell_price * quantity + buy_price * quantity) * self.fee_rate
#                 if trade_profit > 0:
#                     self.profit_trades += 1
#                 else:
#                     self.loss_trades += 1
#                 self.portfolio_performance += trade_profit
#                 self.cash_balance += sell_price * quantity * (1 - self.fee_rate)
#                 if self.portfolio[symbol]['quantity'] == quantity:
#                     del self.portfolio[symbol]
#                 else:
#                     self.portfolio[symbol]['quantity'] -= quantity
#                     self.portfolio[symbol]['buy_price'] = (self.portfolio[symbol]['buy_price'] * self.portfolio[symbol][
#                         'quantity'] + sell_price * quantity) / (self.portfolio[symbol]['quantity'])
#         else:
#             print("Error: {} not in portfolio".format(symbol))
#             return
#         self.trade_performance()
#         print("Closing order: Sold {} {} at {}. Portfolio value: {}".format(quantity, symbol, sell_price,
#                                                                             self.portfolio_value()))
#
#     def sell_all(self, symbol, sell_price):
#         if symbol in self.portfolio:
#             self.add_sell_order(symbol, self.portfolio[symbol]['quantity'], sell_price)
#         else:
#             print("Error: {} not in portfolio".format(symbol))
#             return
#
#     def portfolio_value(self):
#         portfolio_value = self.portfolio_performance + self.cash_balance
#         for symbol in self.portfolio:
#             portfolio_value += self.portfolio[symbol]['buy_price'] * self.portfolio[symbol]['quantity']
#         return portfolio_value
#
#     def trade_performance(self):
#         if self.cash_balance == 0:
#             return "No trade performance can be calculated as there is no trade yet"
#         else:
#             self.portfolio_performance_percentage = (
#                                                            self.portfolio_performance + self.cash_balance) / self.cash_balance * 100
#
#     @staticmethod
#     def combine_portfolios(portfolio_list):
#         combined_portfolio = CryptoPortfolio()
#         for portfolio in portfolio_list:
#             if portfolio is not None:
#                 for symbol, value in portfolio.portfolio.items():
#                     if symbol in combined_portfolio.portfolio:
#                             combined_portfolio.portfolio[symbol]['quantity'] += value['quantity']
#                             combined_portfolio.portfolio[symbol]['buy_price'] = (combined_portfolio.portfolio[symbol][
#                                                                                      'buy_price'] *
#                                                                                  combined_portfolio.portfolio[symbol][
#                                                                                      'quantity'] + value['buy_price'] * value[
#                                                                                      'quantity']) / (
#                                                                                             combined_portfolio.portfolio[
#                                                                                                 symbol]['quantity'] + value[
#                                                                                                 'quantity'])
#                     else:
#                             combined_portfolio.portfolio[symbol] = {'quantity': value['quantity'],
#                                                                     'buy_price': value['buy_price']}
#                 combined_portfolio.initial_investment += portfolio.initial_investment
#                 combined_portfolio.fee_rate = portfolio.fee_rate
#                 combined_portfolio.portfolio_performance += portfolio.portfolio_performance
#                 combined_portfolio.profit_trades += portfolio.profit_trades
#                 combined_portfolio.loss_trades += portfolio.loss_trades
#                 combined_portfolio.cash_balance += portfolio.cash_balance
#         combined_portfolio.trade_performance()
#         return combined_portfolio
#
#     def save_to_json(self, file_name):
#         with open(file_name, 'w') as f:
#             json.dump(self.__dict__, f)
#         print("Portfolio saved to {}".format(file_name))
#
