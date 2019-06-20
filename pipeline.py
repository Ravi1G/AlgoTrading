import pandas as pd
from alpha_vantage.timeseries import TimeSeries
import os
import requests
from bs4 import BeautifulSoup
import io

class Pipeline:
    def __init__(self, universe, start_date, end_date, resolution):
        self.universe = universe
        self.start_date = start_date
        self.end_date = end_date
        self.resolution = resolution
        self.ts = TimeSeries(key=os.environ['AV_API_KEY'], output_format='pandas')

    def init_universe(self):
        if isinstancce(self.universe, list):
            tickers = self.universe
        elif istance(self.universe, string):
            tickers = self._get_constituents()
        return tickers




    def build_prices():
        prices = []
        tickers = self.init_universe()
        for ticker in tickers:
            prices.append()

    def _get_constituents(self):
        last_business_day = (pd.to_datetime(self.start_date) +  \
        pd.offsets.BMonthEnd(-1)).date().strftime('%Y%m%d')
        if self.universe == 'sp500':
            url = 'https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund&asOfDate={}'

        elif self.universe =='russell2000':
            url = 'https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund&asOfDate={}'
        try:
            content = requests.get(url.format(last_business_day))
        except requests.exception.RequestException as e:
            print(e)
        historical_holdings = pd.read_csv(io.StringIO(content.text), skiprows=10)
        tickers = historical_holdings['Ticker'].values

        return tickers
