import sys, pandas as pd
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from lightweight_charts.widgets import QtChart          # ← the embedded version
from ib_async import util          # <— ib_async carries its own util module
import pandas as pd
import ib_async
from ib_async import *
print(ib_async.__all__)
ib = IB()
ib.connect('127.0.0.1', 7496, clientId=10)
contract = Stock('AAPL', 'SMART', 'USD')
daily_bars = ib.reqHistoricalData(
    contract,
    endDateTime='20250530 16:01:00 US/Eastern',
    durationStr='1000 S',
    barSizeSetting='1 min',
    whatToShow='TRADES',
    useRTH=False,
    formatDate=1
)
daily_bars
# bars  = the list of BarData objects you showed
df = util.df(daily_bars)                 # ❶ explode BarData → DataFrame :contentReference[oaicite:0]{index=0}

# keep only what the chart needs and rename “date” → “time”
df = (df[['date', 'open', 'high', 'low', 'close', 'volume']]
        .rename(columns={'date': 'time'}))

# (optional) make the timestamps uniform
df['time'] = (pd.to_datetime(df['time'])       # time-zone-aware
                .dt.tz_convert('UTC'))         # or .dt.tz_localize('US/Eastern')

# (optional) convert to POSIX seconds if you feed a JS-based chart
# df['time'] = df['time'].astype('int64') // 1_000_000_000




app = QApplication(sys.argv)

# --- build your main window --------------------------------------------------
win = QMainWindow()
central = QWidget(win)          # Qt wants one central widget
layout  = QVBoxLayout(central)  # can be HBox/Grid… anything you like
win.setCentralWidget(central)

# --- add the chart widget ----------------------------------------------------
chart = QtChart(central)        # parent keeps it inside the same window
layout.addWidget(chart.get_webview())   # or just layout.addWidget(chart)

# 5-minute bars from CSV, API, or your own stream -----------------------------
chart.set(df)                            # first paint

# live updates while the bar is forming
# chart.update_from_tick(timestamp_ns, last_price, volume)

win.resize(1100, 600)
win.show()
sys.exit(app.exec())

