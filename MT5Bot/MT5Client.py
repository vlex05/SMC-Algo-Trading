from PySide2.QtCore import QThread
import pymt5adapter as mt5
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

import ta

import time,math,datetime


class DataLoop(QThread):

    def __init__(self,parent):
        super(DataLoop, self).__init__()
        self.parent = parent
        self.last = None

    def __del__(self):
        self.wait()

    def run(self):
        print("DataLoop.run()")

        while True:
            # print("loop")

            time.sleep(0.8)
            try:
                self.parent.update()

            except:
                pass

            # print("end of loop")


class MT5Client:

    def __init__(self):

        if not mt5.initialize():
            print("Connexion a mt5 echouée")
            mt5.shutdown()

        self.base_asset = None
        self.pair = "BTCUSD"
        self.interval = mt5.TIMEFRAME_M1
        self.df_length = 30
        self.open_positions = []

        self.position_size = 1 #lot
        self.tp = 0.004
        self.sl = 3 * self.tp
        self.tp1_price = None
        self.trading_fee = 3/100000

        self.trail_stop = 0.85
        self.min_trail = 0.05
        self.max_price = None
        self.TS = None
        self.trail_stop_enabled = True

        self.mode = "trade"
        self.position = -1

        self.trade_history = []
        self.position_open = False
        self.position_data = {}
        self.reset_position()

        self.out_data = {}

        # backtesting data:
        self.backtest_initial_balance = 100000
        self.asset = 0
        # self.backtest_length = 3000
        self.equity_history = []
        self.backtest_epoch = 0
        self.backtest_start = self.df_length
        self.asset_price = None
        self.plot = False

        self.trading_delay = 0.5
        self.update_time = 0
        self.balances = {}
        self.tickers = {}
        self.df = pd.DataFrame()

        self.data_loop = DataLoop(self)

    def start(self):

        if self.mode == "trade":
            self.trade_init()
            self.trade_loop()

        elif self.mode == "backtest":
            self.backtest_init()
            self.backtest_loop()

    def update(self):
        # print("BinanceClient.update()")

        # get account balance
        account_info = mt5.account_info()
        # print(account_info)

        self.update_time = time.time()

        balance = account_info.balance
        self.base_asset = account_info.currency

        balances = {}

        balances[self.base_asset] = float(balance)
        self.balances = balances
        # print(self.balances)

        # get bid & ask price

        _from = time.time() - 200000
        _to = time.time()
        tick = mt5.copy_ticks_range(self.pair, _from, _to, mt5.COPY_TICKS_INFO)

        self.tickers[self.pair] = {"ask": float(tick[0][2]), "bid": float(tick[0][1])}

        # print(self.tickers)

        pos = mt5.positions_get(self.pair)
        # print(pos)
        positions = []
        for i in pos:
            if i.type == 0:
                side = 'long'
            elif i.type == 1:
                side = 'short'

            p= {
                'side': side,
                'lot': i.volume,
                'sl': i.sl,
                'tp': i.tp,
                'open': i.price_open,
                'ticket': i.ticket
            }

            positions.append(p)

        self.open_positions = positions

        # print(self.open_positions)

        self.df = self.get_candles()

    def update_trailstop(self,actual):
        
        if self.mode == "trade":
            trigger = actual["close"]
        
        else:
            trigger = actual["low"]
        
        if self.position_open and self.trail_stop_enabled:
            print(" ----------------  update trail stop -----------------")
            print(" Trigger" + str(trigger) + "  Trail stop:  " + str(self.TS) )

            open_price = self.position_data['buy_price']
            min_trail = open_price * self.min_trail

            trail_trigger = (min_trail / self.trail_stop)+open_price
            
            print("Min trail price: " + str(min_trail+open_price))
            print("Trail stop trigger price: " + str(trail_trigger))


            #  ----------------------  if trail stop touched ---------------------
            if (self.TS is not None) and trigger < self.TS:
                print("trail stop")

                self.asset_price = self.TS
                self.position_data['trail_stop'] = True
                self.sell()

                return True

            print(" Actual high " + str(actual["high"]) + "  Max: " + str(self.max_price))
            # -------------------------- if high > max -------------------
            if self.max_price is None or self.max_price < actual["high"]:

                self.max_price = actual["high"]

                delta = (self.max_price-open_price)
                trail_value = ( delta * self.trail_stop)

                print("Trail value: " + str(trail_value) + "   Min trail value: " + str(min_trail))

                if trail_value > min_trail:
                    self.TS = open_price + trail_value

                    if self.mode == 'trade':

                        print(" TS value updated:" + str(self.TS))
                        pass

            return False

    def trade_init(self):
        self.update()
        self.data_loop.start()
        time.sleep(0.5)

    def backtest_init(self):
        print("backtest init")

        # init equity data
        self.balances = {
            self.base_asset: float(self.backtest_initial_balance),
            self.asset: 0.0
        }
        self.equity_table =[]
        self.trade_table = []

        print("start loading candle data...")
        start_time = time.time()

        # download candlestick
        self.df = self.get_candles()

        duration = round( time.time() - start_time, 2)

        print("candle data received in " + str(duration) + " sec.")

        start_time = time.time()

        self.data_process()

        duration = round( time.time() - start_time, 2)

        print("data processed in " + str(duration) + " sec.")

        # init iteration data

    def data_process(self):
        # print("data_process")
        pass

    def write_order(self, text):
        text += "\n"
        f = open("order.log", 'a')
        f.write(text)
        f.close()

    def write_position(self, text):
        text = str(text)
        text += "\n"
        f = open("position.log", 'a')
        f.write(text)
        f.close()

    def buy(self):

        if self.mode == "trade" :
            self.trade_buy()

        elif self.mode == "backtest":
            self.backtest_buy()

    def sell(self):

        if self.mode == "trade":
            self.trade_sell()

        elif self.mode == "backtest":
            self.backtest_sell()

    def reset_position(self):
        self.position_data = {
            "start_epoch": None,
            "end_epoch": None,
            "buy_price": None,
            "sell_price": None,
            "profit": None,
            "trail_stop": None
        }
        self.position_open = False
        self.max_price = None
        self.drawdown_price = None
        self.TS = None

    def open_position(self,epoch,price):
        epoch = round(epoch)
        price = round(price,5)

        if not self.position_open:

            self.position_open = True

            self.position_data["start_epoch"] = epoch
            self.position_data["buy_price"] = price

    def close_position(self, epoch, price):

        epoch = round(epoch)
        price = round(price, 5)

        if self.position_open:

            self.position_data["end_epoch"] = epoch
            self.position_data["sell_price"] = price

            self.position_data["profit"] = round((self.position_data["sell_price"] / self.position_data["buy_price"] ) - 1,5)

            self.trade_history.append(self.position_data)

            self.write_position(self.position_data)
            self.reset_position()

    def trade_buy(self):

        qty = self.position_size
        symbol = self.pair

        sl = self.sl
        tp = self.tp

        result = self.mt5_buy_market(symbol,qty,None,None)

        ticket = result.order

        time.sleep(0.5)

        trade = mt5.positions_get(ticket=ticket)[0]

        print("open_price: ",trade.price_open)

        price = trade.price_open

        sl = price - (price * self.sl)
        tp = price + (price * self.tp)

        self.mt5_edit_tp(ticket,tp)
        self.mt5_edit_sl(ticket,sl)


    def trade_sell(self):

        to_close = []

        for i in self.open_positions:
            if i['side'] == 'long':
                ticket = i['ticket']
                self.mt5_close_position(ticket)

    def mt5_buy_market(self, symbol, lot, _sl=None, _tp=None):
        print("buy_market()")
        return self.mt5_order_market(symbol, lot, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_market(self, symbol, lot, _sl=None, _tp=None):
        print("sell_market()")
        return self.mt5_order_market(symbol, lot, _type="sell", sl=_sl, tp=_tp)

    def mt5_buy_limit(self, symbol, lot, _sl=None, _tp=None):
        print("buy limit")
        return self.mt5_order_limit(symbol, lot, self.trade_price, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_limit(self, symbol, lot, _sl=None, _tp=None):
        print("sell limit")
        return self.mt5_order_limit(symbol, lot, self.trade_price, _type="sell", sl=_sl, tp=_tp)

    def mt5_order_market(self, symbol, lot, _type="buy", sl=None, tp=None):
        print(
            "  ----------------------------------  order_market()  --------------------------------------------------------------------")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL

        else:
            return False

        lot = float(lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": _type,
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        if sl is not None:
            sl = float(sl)
            request["sl"] = sl

            if tp is not None:
                tp = float(tp)
                request["tp"] = tp

        # print(request)

        result = mt5.order_send(request)
        # print(result)
        return result

    def mt5_order_limit(self, symbol, lot, price, _type="buy", sl=None, tp=None):
        print("order_market()")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY_LIMIT

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL_LIMIT

        else:
            return False

        lot = float(lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": _type,
            "price": price,
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        if sl is not None:
            sl = float(sl)
            request["sl"] = sl

            if tp is not None:
                tp = float(tp)
                request["tp"] = tp

        print(request)

        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_edit_tp(self, ticket, tp):
        print("edit_tp()")

        pos = mt5.positions_get(ticket=ticket)

        sl = pos[0].sl
        symbol = pos[0].symbol

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "tp": tp,
            "sl": sl,
        }

        print(request)
        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_edit_sl(self, ticket, sl):
        print("edit_sl()")

        pos = mt5.positions_get(ticket=ticket)

        tp = pos[0].tp
        symbol = pos[0].symbol

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "tp": tp,
            "sl": sl,
        }

        print(request)
        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_close_position(self, ticket):
        print("close position " + str(ticket))

        pos = mt5.positions_get(ticket=ticket)
        symbol = pos[0].symbol

        print(mt5.Close(ticket))

        print(pos)
        #

        volume = pos[0].volume
        _type = pos[0].type

        if _type == mt5.ORDER_TYPE_BUY:
            print('sell')
            _type = mt5.ORDER_TYPE_SELL
        elif _type == mt5.ORDER_TYPE_SELL:
            print('buy')
            _type = mt5.ORDER_TYPE_BUY
        else:
            return None

        request = {
            # "action": mt5.TRADE_ACTION_CLOSE_BY,
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "type": _type,
            "type_filling": mt5.ORDER_FILLING_FOK

        }

        print(request)
        result = mt5.order_send(request)
        print(result)
        return result

    def backtest_buy(self):
        # print("backtest buy")

        asset = self.balances[self.asset]
        asset_price = self.asset_price
        base_asset = self.balances[self.base_asset]

        self.open_position(self.backtest_epoch, asset_price)

        asset = asset + base_asset/asset_price
        base_asset = 0

        self.balances[self.asset] = asset
        self.balances[self.base_asset] = base_asset

    def backtest_sell(self):
        # print("backtest sell")

        asset = self.balances[self.asset]
        asset_price = self.asset_price
        base_asset = self.balances[self.base_asset]

        self.close_position(self.backtest_epoch, asset_price)

        base_asset = base_asset + asset * asset_price
        base_asset = base_asset * (1 - self.trading_fee)
        asset = 0

        self.balances[self.asset] = asset
        self.balances[self.base_asset] = base_asset

        self.equity_history.append(
            {
                "usd": round(base_asset),
                "timestamp": self.backtest_epoch
            }
        )

    def get_candles(self):
        # print("MT5Bot.get_candles()")

        if self.mode == "trade":
            length = self.df_length

        elif self.mode == "backtest":
            length = self.backtest_length

            # if backtest, check if history exist

            path = self.pair + ".csv"

            if os.path.exists(path):
                df = pd.read_csv(path)

                df_length = df["open"].shape[0]

                if df_length >= length:
                    print(" import dataset from .csv")

                    self.backtest_start = df_length-length + self.df_length
                    self.position = self.backtest_start

                    # print(self.position)

                    df['close'] = pd.to_numeric(df['close'])
                    df['high'] = pd.to_numeric(df['high'])
                    df['low'] = pd.to_numeric(df['low'])
                    df['open'] = pd.to_numeric(df['open'])
                    df['volume'] = pd.to_numeric(df['volume'])
                    df['timestamp'] = pd.to_numeric(df['timestamp'])

                    return df

                else:
                    print(" download dataset")

            else:
                print(" download dataset")

        else:
            length = 0
            return

        _from = round((time.time()-(60*length)-120*60)- 360000)
        _to = round(time.time())

        # print(["from", _from, "to", _to])

        # candles = self.client.get_historical_klines(self.pair,self.interval ,str(start))
        candles = mt5.copy_rates_range(self.pair,self.interval, _from, _to)

        # print(candles)

        cd_data = candles.tolist()



        df = pd.DataFrame(cd_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'spread', 'v2'])
        # print("df converted")
        # print(df)
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        df['volume'] = pd.to_numeric(df['volume'])


        # print(df)

        # df['timestamp'] = pd.to_datetime(df['timestamp'])



        # for i in df.index:
        #     df.at[i,'timestamp']= int(df['timestamp'][i].timestamp()*1000000)


        if self.mode == "backtest":

            df.to_csv(path,index=False)


        return df

    def manager(self):
        pass

    def analyse_data(self):
        # print("analyse_data()")

        self.sell()

        # print(" --------- Equity history -----------")

        equity_history = pd.DataFrame(self.equity_history)
        # print(equity_history)

        print(" ---------------- Backtest result ----------------")

        trading_min = self.backtest_length

        trading_day = round(trading_min / 1440)

        trading_min = trading_min - (trading_day * 1440)

        trading_hour = round(trading_min / 60)
        trading_min = trading_min - (trading_hour * 60)

        print(
            "Backtest duration: " + str(trading_day) + "day " + str(trading_hour) + "hour " + str(trading_min) + "min ")

        df = pd.DataFrame(self.trade_history)

        # print("---------------- Trade history -------------")

        # df = df.sort_values(by=['profit'])

        print(df)

        profitable_trades = df[df['profit'] > 0.005]
        non_profitable_trades = df[df['profit'] < -0.005]

        # print(df)
        #
        # print(self.balances)

        base_asset = self.balances[self.base_asset]

        print("--")

        print("Initial Equity :" + str(self.backtest_initial_balance) + "$")

        print("Final Equity :" + str(round(base_asset)) + "$")

        print("--")

        trade_nb = df.shape[0]

        mean_profit = df['profit'].mean()
        print("Mean profit:" + str(round(mean_profit * 100, 3)) + "%")
        trading_day_dec = round((self.backtest_length / 1440), 2)
        print("Trading days:" + str(trading_day_dec))
        daily_trade_nb = round(trade_nb / trading_day_dec, 2)
        print("Daily_trade_nb:" + str(daily_trade_nb))
        daily_profit = round((mean_profit * daily_trade_nb) * 100, 2)
        print(" ---- ----")

        percent_profit = ((base_asset / self.backtest_initial_balance) - 1) * 100

        profitable_trade_nb = df[df['profit'].between(0.0005, 1, inclusive='right')].shape[0]
        win_rate = round(profitable_trade_nb / trade_nb, 2)

        loss = round(df[df['profit'].between(-1, -0.0005, inclusive='right')].shape[0] / trade_nb * 100, 1)
        profit_BE = round(df[df['profit'].between(-0.0005, 0.0005, inclusive='right')].shape[0] / trade_nb * 100, 1)
        profit = round(df[df['profit'].between(0.0005, 1, inclusive='right')].shape[0] / trade_nb * 100, 1)
        # profit_over_001 = round(
        #     df[df['profit'].between(0.0005, 0.002, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # profit_over_002 = round(
        #     df[df['profit'].between(0.002, 0.004, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # profit_over_004 = round(
        #     df[df['profit'].between(0.004, 0.01, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # profit_over_010 = round(
        #     df[df['profit'].between(0.01, 0.02, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # profit_over_020 = round(
        #     df[df['profit'].between(0.02, 0.03, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # profit_over_030 = round(
        #     df[df['profit'].between(0.03, 1, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        # trail_stopped = round(
        #     profitable_trades[profitable_trades['trail_stop'] == True].shape[0] / profitable_trade_nb * 100, 1)

        mean_profit = round(profitable_trades["profit"].mean(), 4)
        mean_loss = round(non_profitable_trades["profit"].mean(), 4)

        self.out_data = {}

        print("Total profit: " + str(round(percent_profit, 2)) + "%")
        self.out_data["profit"] = percent_profit

        # print("Trail stopped: " + str(round(trail_stopped, 2)) + "%")

        print("Trades: " + str(trade_nb))

        self.out_data["trade_nb"] = trade_nb

        print("Daily profit: " + str(daily_profit) + "%")

        self.out_data["daily_profit"] = daily_profit

        print("--")
        print("WinRate: " + str(win_rate))

        self.out_data["win_rate"] = win_rate

        dd = self.check_drawdown()
        self.out_data["max_drawdown"] = dd

        print("Max Drawdown: " + str(round(dd * 100, 2)) + "%")

        print("Mean profit: " + str(mean_profit))
        self.out_data["mean_profit"] = mean_profit
        print("Mean loss: " + str(mean_loss))
        self.out_data["mean_loss"] = mean_loss
        print(" ---------------- Detailed result ----------------")
        print("--Loss--")
        print("Total loss: " + str(loss) + "%")
        print("--Break Even--")
        print("Total BE(-0.05% => 0.05%) :" + str(profit_BE) + "%")
        print("--Profit--")
        print("Total Profit: " + str(profit) + "%")
        # print("     Trail stop: " + str(profit_over_001) + "%")
        # print("     Profit over 0.05%: " + str(profit_over_001) + "%")
        # print("     Profit over 0.2%: " + str(profit_over_002) + "%")
        # print("     Profit over 0.4%: " + str(profit_over_004) + "%")
        # print("     Profit over 1%: " + str(profit_over_010) + "%")
        # print("     Profit over 2%: " + str(profit_over_020) + "%")
        # print("     Profit over 3%: " + str(profit_over_030) + "%")
        print("-------------------------------------------------")

        self.out_data["equity_history"] = equity_history
        self.out_data["trade_history"] = self.trade_history

        if self.plot:
            equity_history[['usd']].plot()
            plt.show()

        return self.out_data

    def trade_loop(self):
        print("BinanceClient.trade()")

        while True:
            if self.mode == "trade":
                time.sleep(self.trading_delay)
                self.data_process()
                self.manager()

    def backtest_loop(self):
        print("BinanceClient.backtest_loop()")

        start_time = time.time()

        while self.position < self.df.shape[0]:

            # print(self.position)
            # iterate in dataset
            self.manager()

            self.position += 1

        duration = round( time.time() - start_time, 2)

        print("data backtested in " + str(duration) + " sec.")

        start_time = time.time()

        self.analyse_data()

        duration = round( time.time() - start_time, 2)

        print("data analysed in " + str(duration) + " sec.")

    def check_drawdown(self):
        equity = self.equity_history

        dd_history = []


        _max = equity[0]["usd"]
        _min = _max

        data = {
            "min": _min,
            "max": _max,
            "drawdown": 0
        }

        dd_history.append(data)

        for i in equity:
            eq = i['usd']

            if eq > _max:

                if _max > _min:

                    dd = (_min - _max) / _max

                    data = {
                        "min": _min,
                        "max": _max,
                        "drawdown": dd
                    }

                    dd_history.append(data)

                    _max = eq
                    _min = _max

                else:
                    _max = eq

            elif eq < _min:
                _min = eq

        df = pd.DataFrame(dd_history)

        max_dd = df["drawdown"].max()

        return max_dd























