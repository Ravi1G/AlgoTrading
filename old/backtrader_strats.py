import backtrader as bt
import numpy as np
import pandas as pd


class RSI25(bt.Strategy):

    params = (
        ('num_periods_sma', 200),
        ('num_periods_rsi', 4),
        ('buy_lvl_first_unit', 25),
        ('buy_lvl_second_unit', 20),
        ('sell_lvl', 55)
    )

    def __init__(self):

        # two indicators used for strategy: SMA & RSI
        self.sma = bt.ind.SMA(self.data, period=self.params.num_periods_sma)
        self.rsi = bt.ind.RSI(self.data, period=self.params.num_periods_rsi)

        # pre-calculation of the logic in __init__ to speed up computations
        self.first_buy_sig = self.rsi < self.params.buy_lvl_first_unit
        self.second_buy_sig = self.rsi < self.params.buy_lvl_second_unit
        self.sell_sig = self.rsi > self.params.sell_lvl

    def next(self):

        if not self.position:
            if self.first_buy_sig:
                self.buy(size=1000, exectype=bt.Order.Close)

        else:
            if self.second_buy_sig and self.position.size == 1000:
                self.buy(size=2000, exectype=bt.Order.Close)

            if self.sell_sig:
                self.close(exectype=bt.Order.Close)


class RotationalRSI25(bt.Strategy):

    params = (
        ('num_periods_sma', 200),
        ('num_periods_rsi', 4),
        ('buy_lvl_first_unit', 25),
        ('buy_lvl_second_unit', 20),
        ('sell_lvl', 55),
        ('cheat_on_close', True)
    )

    def __init__(self):
        self.sma = dict()
        self.rsi = dict()
        self.first_buy_sig = dict()
        self.second_buy_sig = dict()
        self.sell_sig = dict()

        self.o = dict()  # orders per data (main, stop, limit, manual-close)
        self.holding = dict()  # holding periods per data

        self.broker.set_coc(self.p.cheat_on_close)
        for d in self.getdatanames():
            self.sma[d] = bt.ind.SMA(self.getdatabyname(d), period=self.params.num_periods_sma)
            self.rsi[d] = bt.ind.RSI(self.getdatabyname(d), period=self.params.num_periods_rsi, safediv=True)

            # pre-calculation of the logic in __init__ to speed up computations
            self.first_buy_sig[d] = self.rsi[d] < self.params.buy_lvl_first_unit
            self.second_buy_sig[d] = self.rsi[d] < self.params.buy_lvl_second_unit
            self.sell_sig[d] = self.rsi[d] > self.params.sell_lvl

    def notify_order(self, order):
        if order.status == order.Submitted:
            return

        dt, dn = self.datetime.date(), order.data._name
        print('{} {} Order {} Status {}'.format(
            dt, dn, order.ref, order.getstatusname())
        )

        whichord = ['main', 'stop', 'limit', 'close']
        if not order.alive():  # not alive - nullify
            dorders = self.o[order.data]
            idx = dorders.index(order)
            dorders[idx] = None
            print('-- No longer alive {} Ref'.format(whichord[idx]))

            if all(x is None for x in dorders):
                dorders[:] = []

    def next(self):

        for i, d in enumerate(self.datas):
            dt, dn = self.datetime.date(), d._name
            pos = self.getposition(d).size
            print('{} {} Position {}'.format(dt, dn, pos))
            if not pos and not self.o.get(d, None):


        for d in self.getdatanames():

            if not self.getpositionbyname(d).size:
                if self.first_buy_sig[d]:
                    self.buy(data=self.getdatabyname(d), size=1)

            else:
                if self.second_buy_sig[d]:
                    self.buy(data=self.getdatabyname(d), size=1)
                if self.sell_sig[d]:
                    self.close(data=self.getdatabyname(d))


class SCTR(bt.Strategy):
    params = (
        ('n_positions', 50),
        ('short', True)
    )

    def __init__(self):

        for d in self.getdatanames():
            # long term indicators
            self.sma_200d[d] = bt.ind.SMA(self.getdatabyname(d), period=125)
            self.roc_125d[d] = bt.ind.RateOfChange(self.getdatabyname(d), period=125)
            # mid-term indicators
            self.sma_50d[d] = bt.ind.SMA(self.getdatabyname(d), period=50)
            self.roc_20d[d] = bt.ind.RateOfChange(self.getdatabyname(d), period=20)
            # short-term indicators
            self.rsi_14d[d] = bt.ind.RSI(self.getdatabyname(d), period=14)
            self.ppo[d] = bt.ind.PercentagePriceOscillator(self.getdatabyname(d))
            self.ppo_signal_line[d] = bt.ind.EMA(self.ppo[d], period=9)
            self.ppo_hist[d] = self.ppo[d] - self.ppo_signal_line[d]

            self.SCTR[d] = 0.3 * 100 * (self.getdatabyname(d) - self.sma_200d[d]) / self.sma_200d[d] + \
                0.3 * self.roc_125d[d] + 0.15 * 100 * (self.getdatabyname(d) - self.sma_50d[d]) / self.sma_50d[d] + \
            0.15 * self.roc_20d[d] + 0.05 * self.rsi_14d[d] + 0.05 * (self.ppo_hist[d][0] - self.ppo_hist[d][-3])/3.0

    def next(self):
        sctr_ls = np.array([self.SCTR[d] for d in self.getdatanames()])
        high_threshold = np.percentile(sctr_ls, 90)
        low_threshold = np.percentile(sctr_ls, 10)
        for d in self.getdatanames():
            pass
