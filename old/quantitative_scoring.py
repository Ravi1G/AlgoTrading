from backtest import Strategy, Portfolio
import pandas as pd
import numpy as np


class DailyScoreStrategy(Strategy):

    def __init__(self, bars, n_positions=50, how='long/short'):
        self.bars = bars
        self.n_positions = n_positions
        self.how = how

    def generate_signals(self):
        self.scores = self._compute_scores(self.bars)
        signals = self._compute_mask(self.scores, self.n_positions, self.how)
        return signals

    def _compute_scores(self, input_data):
        """
        Implementation of Stock chart technical ranking:
        https://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:sctr
        :param input_data: stacked daily OHLCV bars
        :return: daily score for each equity
        """
        grouped = input_data.groupby(by='ticker')
        df = None
        for name, subgroup in grouped:
            group = subgroup.copy()
            # percent above 200 days moving average
            perc_200d_ma = 100*(group['Close'] - group['Close'].ewm(span=200, min_periods=199).mean()) / \
                           group['Close'].ewm(span=200, min_periods=199).mean()
            # 125 days ROC
            M = group['Close'].diff(125)
            N = group['Close'].shift(125)
            roc125 = 100*(M/N)
            # percent above 50 days moving average
            perc_50d_ma = 100*(group['Close'] - group['Close'].ewm(span=50, min_periods=49).mean()) / \
                           group['Close'].ewm(span=50, min_periods=49).mean()
            # 20 days ROC
            M = group['Close'].diff(20)
            N = group['Close'].shift(20)
            roc20 = 100*(M/N)
            # 14 days RSI
            rsi = self._RSI(group)
            # 3-days slope of PPO-histogram
            ppo = 100*((group['Close'].ewm(span=12, min_periods=11).mean() - \
                        group['Close'].ewm(span=26, min_periods=25).mean() / \
                        group['Close'].ewm(span=26, min_periods=25).mean()))
            signal_line = ppo.ewm(span=9).mean()
            ppo_hist = (ppo - signal_line).diff(3) / 3.0
            group['score'] = 0.3*perc_200d_ma + 0.3*roc125 + 0.15*perc_50d_ma + 0.15*roc20 + 0.05*rsi + 0.05*ppo_hist
            df = pd.concat([df, group], axis=0)
        df = df.pivot(index='Date', columns='ticker', values='score')
        df = df.dropna(axis=0, how='all')
        return df

    def _RSI(self, df, n=14):
        dates = df.index
        UpI = [0]
        DoI = [0]
        for i in range(1, len(dates)):
            U = max([df.at[dates[i], 'Close'] - df.at[dates[i-1], 'Close'], 0])
            D = max([df.at[dates[i-1], 'Close'] - df.at[dates[i], 'Close'], 0])
            UpI.append(U)
            DoI.append(D)
        UpI = pd.Series(UpI, index=dates)
        DoI = pd.Series(DoI, index=dates)
        RS = UpI.ewm(span=n, min_periods=n-1).mean() / DoI.ewm(span=n, min_periods=n-1).mean()
        return 100 - 100/(1+RS)

    def _compute_mask(self, scores, top_n, how='long/short'):
        #scores = scores.dropna(axis=0, how='all')
        top_n_scores = scores.copy()
        top_n_scores[:] = 0
        for date, scores in scores.iterrows():
            top_n_scores.loc[date, scores.nlargest(top_n).index] = 1
            if how == 'long/short':
                top_n_scores.loc[date, scores.nsmallest(top_n).index] = -1
        return top_n_scores

class DailyPortfolio(Portfolio):

    def __init__(self, bars, signals, initial_capital=1e6, fees=5):
        self.bars = bars.loc[signals.index]
        self.signals = signals
        self.initial_capital = initial_capital
        self.fees = fees

    def generate_weights(self, strategy='uniform', scores=None):
        if strategy == 'uniform':
            self.weights = self.signals.divide(self.signals.abs().sum(axis=1), axis=0)
        elif strategy == 'score':
            self.weights = scores.copy()
            self.weights[:] = 0
            self.weights = (scores.abs() * self.signals).divide(scores.abs() * self.signals.abs().sum(axis=1), axis=0)
            self.weights.fillna(0, inplace=True)

    def backtest_portfolio(self):
        current_pf_val = self.initial_capital
        num_shares = self.signals.copy()
        positions = self.bars.copy()
        pf_vals = pd.Series(index=self.signals.index, name='portfolio_values')
        rets = self.bars.diff().shift(-1)
        for date, prices in self.bars.iterrows():
            num_shares.loc[date] = np.trunc(current_pf_val * self.weights.loc[date] / prices)
            capital_reinvested = (np.abs(num_shares.loc[date]) * prices).sum()
            positions.loc[date] = num_shares.loc[date] * prices
            positions.loc[date, 'cash'] = current_pf_val - capital_reinvested
            current_pf_val += (num_shares.loc[date] * rets.loc[date]).sum()
            current_pf_val -= self.fees*0.01/100*capital_reinvested
            pf_vals.loc[date] = current_pf_val

        returns = pd.DataFrame(data=pf_vals)
        returns['returns'] = returns['portfolio_values'].pct_change()
        num_shares_stacked = pd.DataFrame(num_shares[num_shares != 0].stack())
        num_shares_stacked = num_shares_stacked.rename(columns= {0: 'amount'})
        prices_stacked = pd.DataFrame(self.bars.stack())
        prices_stacked = prices_stacked.rename(columns={0: 'price'})
        transactions = pd.concat([num_shares_stacked, prices_stacked], axis=1, join='inner').reset_index().set_index('Date')
        transactions = transactions.rename(columns={'ticker': 'symbol'})
        return returns, positions, transactions

