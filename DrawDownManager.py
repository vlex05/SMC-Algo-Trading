import matplotlib.pyplot as plt
from random import *

class DrawDownManager():
    def __init__(self, max_dd=0.05, dd_factor=10, du_factor=5):
        self.max_open_loss = 0
        self.max_dd = max_dd
        self.dd_factor = dd_factor
        self.du_factor = du_factor
        self.drawdown = None
        self.drawup = None
        self.is_drawdown = False
        self.equity_data = []
        self.actual_equity = None
        self.min = None
        self.max = None
        self.last_max = None
        self.strategy = 0
        self.R = None
        self.R_value = None

    def preprocess(self):
        equity = self.equity_data

        if len(equity) < 3:
            equity.append(equity[-1]*1.00001)
            equity.append(equity[-1]/1.00001)

        eq_move = []

        _max = equity[0]
        _min = _max

        for i in range(1,len(equity)):
            last = equity[i-1]
            actual = equity[i]
            if actual > last:
                dir = 'up'
            else:
                dir = 'down'
            eq_move.append([last,actual,dir])

        eq_move2 = []
        i = 1
        last = eq_move[0]
        while True:
            actual = eq_move[i]
            if last[2] == actual[2]:
                last[1] = actual[1]
                i+=1
            else:
                eq_move2.append(last)
                last = actual
                i+=1

            if i >= len(eq_move):
                eq_move2.append(last)
                break

        eq_move = eq_move2
        eq_move2 = []

        # sort and keep only up + last and first if down
        if eq_move[0][2] == 'down':
            eq_move2.append(eq_move[0])

        for i in eq_move:
            if i[2] == 'up':
                eq_move2.append(i)

        if eq_move[-1][2] == 'down':
            eq_move2.append(eq_move[-1])



        if eq_move2[0][2] == "down":
            _max = eq_move2[0][0]
        else:
            _max = eq_move2[0][1]

        last_max = _max

        for i in eq_move2:
            if i[2] == "up":
                if i[1] > _max:
                    last_max = _max
                    _max = i[1]

        start = False

        out = []
        for i in eq_move2:
            if start or i[1] == _max:
                out.append(i)
                start = True

        _min = _max

        for i in range(1,len(out)):
            if out[i][0] < _min and out[i][2] == 'up':
                _min = out[i][0]
        # print("-*-")
        # print(out[-1])
        if out[-1][2] == 'down':
            if out[i][1] < _min:
                _min = out[i][1]

        self.equity_data = eq_move2
        self.min = _min
        self.max = _max
        self.last_max = last_max
        self.actual_equity = out[-1][1]

        if self.actual_equity < self.max:
            self.is_drawdown = True
        else:
            self.is_drawdown = False

        if self.is_drawdown:
            self.drawdown = (self.max - self.actual_equity) / self.max
            self.drawup = None
        else:
            self.drawup = -(self.last_max - self.max) / self.last_max
            self.drawdown = None

    def process(self):
        if self.strategy == 0:

            # including PnL if all SL hit right now
            worst = self.actual_equity - self.max_open_loss

            if worst < self.max:
                drawdown = (self.max - worst) / self.max
                drawup = None
                is_drawdown = True
            else:
                drawup = -(self.last_max - self.max) / self.last_max
                drawdown = None
                is_drawdown = False

            if is_drawdown:
                remain = self.max_dd - drawdown
                self.R = round(remain/self.dd_factor,4)
                if self.R < (self.max_dd/self.dd_factor/50):
                    self.R = (self.max_dd/self.dd_factor/50)

            else:
                self.R = (self.max_dd / self.dd_factor) + (drawup/self.du_factor)
                if self.R > 0.5 * self.dd_factor:
                    self.R = 0.5 * self.dd_factor

            self.R_value = round(self.actual_equity * self.R,5)

    def load_data(self, dataset):
        if type(dataset) == list:
            if len(dataset) > 0:
                self.equity_data = dataset

                self.preprocess()
                self.process()


def max_loss():
    # --------------------- test ----------------
    test_nb = 100

    data_history = []

    for dd_factor in range(5, 50, 5):
        ddm = DrawDownManager(0.05, dd_factor, 5)
        dataset = [100.0]
        for i in range(test_nb):
            ddm.load_data(dataset)
            # print(ddm.actual_equity)
            # print(ddm.R_value)
            next = ddm.actual_equity - ddm.R_value
            dataset.append(next)
            # print("----------")

        data_history.append(dataset)

    for i in data_history:
        plt.plot(i[2:])
    # plt.plot(save1)
    # plt.plot(save2)
    plt.show()

def random_trade_generator(nb, win_rate = 0.2, be_rate = 0.3, max_rr = 5):
    # ---------------------- random trade result generator ---------------------
    trade_number = nb

    max_r = max_rr

    win_nb = round(win_rate * trade_number)
    be_nb = round(be_rate * trade_number)
    loss_nb = trade_number - be_nb - win_nb

    # generate loss trade
    trades = []
    for i in range(loss_nb):
        out = -(randrange(60,140,1))/100
        trades.append(out)

    # generate be trades
    for i in range(be_nb):
        out = (randrange(0,200,1)-100)/100
        trades.append(out)

    # generate win trades
    for i in range(win_nb):
        out = randrange(100,100*max_r,1)/100
        trades.append(out)

    shuffle(trades)
    shuffle(trades)

    return trades

def test_equity():


    data_history = []
    total_trades = []
    raw_history = []
    risk = []

    max_dd = 0.2
    dd_factor = 15
    du_factor = 5 * dd_factor

    static_r = max_dd / dd_factor

    for tt in range(200):
        trades = random_trade_generator(200,0.4,0.2,10)
        ddm = DrawDownManager(max_dd, dd_factor, du_factor)
        dataset = [100.0]
        dataset2 = [100.0]
        r = []
        r2 = []
        for i in trades:
            ddm.load_data(dataset)
            next = ddm.actual_equity +(ddm.R_value * i)
            dataset.append(next)
            r.append(ddm.R_value)
            dataset2.append( dataset2[-1] +  (static_r * i * dataset2[-1]))
            r2.append(static_r * dataset2[-1])
            # print("----------")

        data_history.append(dataset)
        raw_history.append(dataset2)
        risk.append([r,r2])
        total_trades += trades

    fig, (ax1,ax2) = plt.subplots(nrows=2,ncols=1)

    for i in data_history:
        ax1.plot(i[2:])
    ax1.grid()


    for i in raw_history:
        ax2.plot(i)
    ax2.grid()

    # ax2.plot(risk[0][0],'r')
    # ax2.plot(risk[0][1],'c')

    # ax2.hist(total_trades, 20, density=True)


    plt.show()


test_equity()






