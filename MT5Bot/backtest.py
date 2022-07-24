from MT5Client import MT5Client
import time, datetime
import pandas as pd
import ta
import pickle


class TraderClient(MT5Client):

    def __init__(self):
        MT5Client.__init__(self)
        self.last = None

        self.ma1 = 2
        self.ma2 = 20

        self.ma3 = 100
        self.ma4 = 2100

    def data_process(self):

        df = self.df

        df['MA1'] = ta.trend.sma_indicator(close=df['close'], window=self.ma1, fillna=True)
        df['MA2'] = ta.trend.sma_indicator(close=df['close'], window=self.ma2, fillna=True)
        df['MA3'] = ta.trend.sma_indicator(close=df['close'], window=self.ma3, fillna=True)
        df['MA4'] = ta.trend.sma_indicator(close=df['close'], window=self.ma4, fillna=True)
        df['delta'] = df['MA1'] - df['MA2']

        self.df = df

    def manager(self):
        # print('manager')

        df = pd.DataFrame(self.df)
        # print(df)

        last = df.iloc[self.position-1]
        actual = df.iloc[self.position]

        self.backtest_epoch = int(actual['timestamp'])
        # print(self.backtest_epoch)

        self.asset_price = actual["close"]
        # print(self.asset_price)

        ts = self.update_trailstop(actual)

        if ts:
            return 1

        if actual['MA3'] > actual['MA4']:
            trend = "bull"
        else:
            trend = 'bear'

        if last["delta"] < 0 and actual["delta"] > 0 and (self.last == 'under' or self.last == None) : #and trend == 'bull'
            # print("_cross over")
            self.last = 'over'
            self.buy()


        elif actual["delta"] < 0 and (self.last == 'over' or self.last == None):
            # print("_under")
            self.last = 'under'
            self.sell()


backtest = TraderClient()

def init():

    backtest.__init__()
    backtest.trade_history = []
    backtest.df_length = 60
    backtest.TS = None
    backtest.trail_stop_enabled = False
    # backtest.tp = 0.001
    # backtest.sl = 2 * backtest.tp
    backtest.pair = "EURUSD"
    backtest.mode = "backtest"
    backtest.backtest_initial_balance = 100000
    backtest.trading_fee =  0 #3 / 100000

test = 0

out = []

r1 =range(2,20,1)
r2 =range(5,60,1)
# r3 =range(90,95,5)
# r4 =range(5,10,5)
#
param = []


# for p1 in r1:
#     for p2 in r2:
#         for p3 in r3:
#             p3 = p3/100
#             for p4 in r4:
#                 p4 = p4/1000
#                 param.append([p1,p2,p3,p4])

# for p1 in r1:
#     for p2 in r2:
#         param.append([p1, p2, 0.90, 0.005])

param.append([20,4, 0.90, 0.005])




print("----------------------- Parameter set ----------------------------")
for i in param:
    print(i)

test_nb = len(param)

print("----------------------- Start backtesting ----------------------------")

start = time.time()

for i in param:

    p1 = i[0]
    p2 = i[1]
    p3 = i[2]
    p4 = i[3]

    if p1 == p2:
        continue

    print(" --- Backtesting ---")
    print([p1,p2,p3,p4])

    init()
    backtest.backtest_length = 30000

    backtest.plot = True

    backtest.ma1 = p1
    backtest.ma2 = p2

    backtest.trail_stop = p3
    backtest.min_trail = p4

    backtest.ma3 = 100
    backtest.ma4 = 700

    result = backtest.start()
    # print(result)
    backtest.out_data["ma1"] = backtest.ma1
    backtest.out_data["ma2"] = backtest.ma2
    backtest.out_data["trail_stop"] = backtest.trail_stop
    backtest.out_data["min_trail"] = backtest.min_trail

    out.append(backtest.out_data)

    total_duration = time.time() - start

    print("total duration:" + str(round(total_duration,2)) + "sec.")

    test += 1

    unit_duration = total_duration / test

    print("Avg duration:" + str(round(unit_duration,2)) + "sec.")

    remain = round((test_nb - test) * unit_duration,2)

    print("remain = > "+ str(test_nb - test) + " test = >" + str(remain) + "sec.")

    planned_end = datetime.datetime.fromtimestamp(time.time() + remain)

    print("end planned on " + str(planned_end) )


# print("**********************************************")
# print(out)


out_df = pd.DataFrame(out)
#
# out_df = out_df[out_df['profit'] > 0]
#
# out_df = out_df.sort_values(by='profit')

print(out_df)

path = str(int(time.time())) + ".save"

# out_df.to_csv(path,index=False)

with open(path, 'wb') as handle:
    pickle.dump(out_df, handle, protocol=pickle.HIGHEST_PROTOCOL)

print("Nb test: " + str(test))




