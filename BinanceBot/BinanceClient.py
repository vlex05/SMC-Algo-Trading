from binance.client import Client
from PySide2.QtCore import QThread

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
        self.client = self.parent.client
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


class BinanceClient:

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

        self.base_asset = "BUSD"
        self.asset = "BTC"
        self.pair = "BTCBUSD"
        self.interval = "1m"
        self.df_length = 30

        self.tp = [0.0002,0.0004]
        self.tp_ratio = [0.5,0.5]
        self.tp1_price = None

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
        # self.backtest_length = 3000
        self.equity_history = []
        self.backtest_epoch = 0
        self.backtest_start = self.df_length
        self.asset_price = None
        self.plot = False

        self.trading_delay = 0.5
        self.client = Client(self.api_key, self.api_secret)
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

        try:

            binance_info = self.client.get_account()

        except:
            print("cannot get account info from binance")

            return

        self.update_time = time.time()

        balance = binance_info['balances']

        balances = {}
        for i in balance:
            if float(i["free"]) > 0.0:
                balances[i["asset"]] = float(i["free"])
        self.balances = balances

        # get bid & ask price

        try:

            tickers = self.client.get_orderbook_tickers()

        except:
            print("cannot get ticker info from binance")

            return



        for i in tickers:
            if i["symbol"] == self.pair:
                self.tickers[self.pair] = {"ask": float(i["askPrice"]), "bid": float(i["bidPrice"])}

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
        print("data_process")
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
        price = round(price,2)

        if not self.position_open:

            self.position_open = True

            self.position_data["start_epoch"] = epoch
            self.position_data["buy_price"] = price

    def close_position(self, epoch, price):

        epoch = round(epoch)
        price = round(price, 2)

        if self.position_open:

            self.position_data["end_epoch"] = epoch
            self.position_data["sell_price"] = price

            self.position_data["profit"] = round((self.position_data["sell_price"] / self.position_data["buy_price"] ) - 1,5)

            self.trade_history.append(self.position_data)

            self.write_position(self.position_data)
            self.reset_position()

    def trade_buy(self):

        # print("buy")

        tp1 = self.tp[0]
        # tp2 = self.tp[1]

        # print(self.balances)

        busd = self.balances[self.base_asset]

        if busd > 10:

            btc_price = self.tickers[self.pair]["ask"]
            btc_amount = math.floor(busd / btc_price*10000)/10000

            # print(btc_amount)

            try:
    
                order = self.client.order_market_buy(
                    symbol=self.pair,
                    quantity=btc_amount)

                if order["status"] == "FILLED":

                    qty = float(order["executedQty"])
                    busd_amount = float(order["cummulativeQuoteQty"])

                    price = busd_amount / qty

                    self.open_position(time.time(),price)
                    sell_price_1 = round(price * (1 + tp1), 2)
                    print(datetime.datetime.now())
                    print("Buy order filled, qty = " + str(qty) + self.asset + " @ " + str(price) + self.base_asset + " TP1 " + str(sell_price_1))


                    # sell_price_2 = round(price * (1 + tp2), 2)

                    # text = "BUY " + str(qty) + " @ " + str(price) + " TP1 " + str(sell_price_1) + " TP2 " + str(sell_price_2)
                    text = "BUY " + str(qty) + " @ " + str(price) + " TP1 " + str(sell_price_1)
                    # text = "BUY " + str(qty) + " @ " + str(round(price,2))
                    self.write_order(text)

                    qty_1 = round(qty*self.tp_ratio[0],6)
                    # qty_2 = qty - qty_1

                    # print("qty 1: " + str(qty_1))
                    # print("qty 2: " + str(qty_2))
                    #
                    # print("TP1")

                    order1 = self.client.order_limit_sell(
                        symbol=self.pair,
                        quantity=qty_1,
                        price=sell_price_1)

                    self.tp1_price = sell_price_1
                    #
                    # print("TP2")
                    #
                    # order2 = self.client.order_limit_sell(
                    #     symbol=self.pair,
                    #     quantity=qty_2,
                    #     price=sell_price_2)

                else:
                    print("---------- ORDER NOT FILLED -----------------")

            except:
                print("------ error during buy order")

        else:
            print("insuficient fund to buy")

    def trade_sell(self):

        # try:
        while True:
            try:

                orders = self.client.get_open_orders(symbol=self.pair)
                break

            except:
                print("error during get_open_order")
                time.sleep(0.3)

        for i in orders:
            order_id = i["orderId"]

            self.client.cancel_order(symbol=self.pair,orderId=order_id)

        self.update()


        btc = self.balances[self.asset]
        # print(btc)

        if btc > 0.0005:
            print("sell")

            qty = math.floor(btc*10000)/10000
            print(qty)

            order = self.client.order_market_sell(
                symbol=self.pair,
                quantity=qty)

            if order['status'] != 'FILLED':
                print("ERROR DURING SELL ORDER")

            else:
                qty = float(order["executedQty"])
                busd_amount = float(order["cummulativeQuoteQty"])

                price = busd_amount / qty

                self.close_position(time.time(),price)

                print(datetime.datetime.now())
                print("Sell order filled, qty = " + str(qty) + self.asset + " @ " + str(price) + self.base_asset)

                text = "SELL " + str(qty) + " @ " + str(round(price,2))
                self.write_order(text)

        else:
            print("else")
            if self.position_open:
                self.close_position(time.time(), self.tp1_price)
                self.tp1_price = None
        # except:
        #     print("error during sell order")

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

        start = ((time.time()-(60*length)-120*60)*1000)

        try:

            candles = self.client.get_historical_klines(self.pair,self.interval ,str(start))

            out = []

            for i in candles:
                out.append(i[0:6])

            candles = out

            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['open'] = pd.to_numeric(df['open'])
            df['volume'] = pd.to_numeric(df['volume'])

            df['timestamp'] = pd.to_datetime(df['timestamp'])

            for i in df.index:
                df.at[i,'timestamp']= int(df['timestamp'][i].timestamp()*1000000)


            if self.mode == "backtest":

                df.to_csv(path,index=False)


            return df

        except:
            print(" cannot download candle data")
            return self.df

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
        profit_over_001 = round(
            df[df['profit'].between(0.0005, 0.002, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        profit_over_002 = round(
            df[df['profit'].between(0.002, 0.004, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        profit_over_004 = round(
            df[df['profit'].between(0.004, 0.01, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        profit_over_010 = round(
            df[df['profit'].between(0.01, 0.02, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        profit_over_020 = round(
            df[df['profit'].between(0.02, 0.03, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        profit_over_030 = round(
            df[df['profit'].between(0.03, 1, inclusive='right')].shape[0] / profitable_trade_nb * 100, 1)
        trail_stopped = round(
            profitable_trades[profitable_trades['trail_stop'] == True].shape[0] / profitable_trade_nb * 100, 1)

        mean_profit = round(profitable_trades["profit"].mean(), 4)
        mean_loss = round(non_profitable_trades["profit"].mean(), 4)

        self.out_data = {}

        print("Total profit: " + str(round(percent_profit, 2)) + "%")
        self.out_data["profit"] = percent_profit

        print("Trail stopped: " + str(round(trail_stopped, 2)) + "%")

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
        print("     Trail stop: " + str(profit_over_001) + "%")
        print("     Profit over 0.05%: " + str(profit_over_001) + "%")
        print("     Profit over 0.2%: " + str(profit_over_002) + "%")
        print("     Profit over 0.4%: " + str(profit_over_004) + "%")
        print("     Profit over 1%: " + str(profit_over_010) + "%")
        print("     Profit over 2%: " + str(profit_over_020) + "%")
        print("     Profit over 3%: " + str(profit_over_030) + "%")
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

        for i in equity:
            eq = i['usd']

            if eq > _max:

                if _max > _min:

                    dd = (_max - _min) / _max

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




















