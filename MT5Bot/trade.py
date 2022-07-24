from MT5Client import MT5Client
import time,datetime
import pandas as pd
import ta
import pickle
import pymt5adapter as mt5

import sys


class LoggingPrinter:
    def __init__(self):
        # self.out_file = open("trade_py.log", 'a')
        self.old_stdout = sys.stdout
        # this object will take over `stdout`'s job
        sys.stdout = self
    # executed when the user does a `print`

    def write(self, text):

        self.out_file = open("trade_py.log", 'a')
        self.old_stdout.write(text)
        self.out_file.write(text)
        self.out_file.close()
    # executed when `with` block begins

    def __enter__(self):
        return self
    # executed when `with` block ends

    def __exit__(self, type, value, traceback):

        # we don't want to log anymore. Restore the original stdout object.
        sys.stdout = self.old_stdout


class TraderClient(MT5Client):

    def __init__(self):
        MT5Client.__init__(self)
        self.last = None

        self.ma1 = 2
        self.ma2 = 20

        self.ma3 = 100
        self.ma4 = 2100

        self.last_delta_saved = None
        self.actual_delta_saved = None

    def data_process(self):

        df = self.df

        df['MA1'] = ta.trend.ema_indicator(close=df['close'], window=self.ma1, fillna=True)
        df['MA2'] = ta.trend.sma_indicator(close=df['close'], window=self.ma2, fillna=True)
        df['MA3'] = ta.trend.sma_indicator(close=df['close'], window=self.ma3, fillna=True)
        df['MA4'] = ta.trend.sma_indicator(close=df['close'], window=self.ma4, fillna=True)
        df['delta'] = round(df['MA1'] - df['MA2'],3)

        self.df = df

    def manager(self):

        df = pd.DataFrame(self.df)

        if self.mode == "trade":
            position = -2
            # position = -1

        else:
            position = self.position

        last2 = df.iloc[position - 2]
        last = df.iloc[position-1]
        actual = df.iloc[position]

        instant = df.iloc[-1]

        self.backtest_epoch = actual['timestamp']

        self.asset_price = actual["close"]

        if self.mode =="trade":
            ts_base = instant

        else:
            ts_base = actual

        ts = self.update_trailstop(ts_base)

        if ts:
            return 1

        if actual['MA3'] > actual['MA4']:
            trend = "bull"
        else:
            trend = 'bear'

        if self.last_delta_saved != last["delta"] or self.actual_delta_saved != actual["delta"]:
            self.last_delta_saved = last["delta"]
            self.actual_delta_saved = actual["delta"]

            slope = actual['MA2'] - last['MA2']

            nw = datetime.datetime.now()
            td = datetime.timedelta(hours=0)
            nw = nw + td
            nw = str(nw.hour) +"H"+str(nw.minute) +"m"+str(nw.second)



            print(nw + "  Last2 delta:" + str(last2["delta"]) +"  Last delta:" + str(last["delta"]) + " Actual delta:" + str(actual["delta"]) + " Slope:" + str(round(slope,2)))

            if last["delta"] < 0 and last2["delta"] < 0 and actual["delta"] > 0 and (self.last == 'under' or self.last == None) and slope >0: #and trend == 'bull'
                print(str(time.time()) + ": cross over")
                self.last = 'over'
                self.buy()

            if (actual["delta"] < 0 and (self.last == 'over' or self.last is None)) and self.TS is None:
                print(str(time.time()) + ": under")
                self.last = 'under'
                self.sell()


with LoggingPrinter():
    trader = TraderClient()

    trader.trade_history = []
    # trader.base_asset = "BUSD"
    # trader.asset = "BTC"
    trader.pair = "BTCUSD"
    trader.interval = mt5.TIMEFRAME_M1
    trader.df_length = 30
    trader.trail_stop_enabled = False
    trader.mode = "trade"
    trader.plot = False

    trader.ma1 = 5
    trader.ma2 = 7

    trader.tp = 0.004
    trader.sl = 3 * trader.tp
    # trader.tp_ratio = [1]

    trader.update()
    time.sleep(0.3)
    trader.start()



