#!.venv/bin/python

"""
Buy High, Sell Higher

Prototype of a simple bot for trading cryptocurrencies following basic trading analysis signals such as Average Directional Movement Index (ADX), Moving Average Convergence Divergence (MACD), and Relative Strength Index (RSI).
"""

# %%
import os
from datetime import datetime

import ccxt
import numpy as np
import talib
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track
from rich.table import Table

# %%
load_dotenv()

BALANCE = int(os.environ["BALANCE"])
CURRENCIES = os.environ["CURRENCIES"].split()
LIVE_TRADE = os.environ["LIVE_TRADE"] == "True"
QUOTE_CURRENCY = os.environ["QUOTE_CURRENCY"]
VARIATION = float(os.environ["VARIATION_%"])

client = ccxt.ftx()
client_params = {"subaccount": os.environ["FTX_SUBACCOUNT"]}
client.apiKey = os.environ["FTX_PUBLIC_KEY"]
client.secret = os.environ["FTX_SECRET_KEY"]

if LIVE_TRADE:
    client.cancel_all_orders(params=client_params)

# %%
def main():
    """Main function."""
    console = Console()
    table = Table(
        title=f"Buy High, Sell Higher ({datetime.strftime(datetime.now(), '%Y-%m-%d')})"
    )

    table.add_column("Time", no_wrap=True)
    table.add_column("Pair", no_wrap=True)
    table.add_column("Balance", no_wrap=True)
    table.add_column("Profit", no_wrap=True)
    table.add_column("Action", no_wrap=True)
    table.add_column("Signals", no_wrap=True)

    account_balances = client.fetch_balance(params=client_params)
    tickers = client.fetch_tickers(
        symbols=[f"{currency}/{QUOTE_CURRENCY}" for currency in CURRENCIES]
    )

    for currency in track(CURRENCIES, description="Processing..."):
        action, colour = "WAIT", "white"
        signals = ""
        symbol = f"{currency}/{QUOTE_CURRENCY}"
        price = float(tickers.get(symbol).get("last"))
        trading_amount = 0

        balance = float(account_balances.get(currency).get("total")) or 0
        # balance = 0
        balance_usd = balance * price
        balance_usd_diff = balance_usd - BALANCE
        variation = (balance_usd / BALANCE * 100) - 100

        if abs(variation) >= VARIATION:
            ohlcv = client.fetch_ohlcv(symbol, timeframe="1m", limit=1440)
            high = np.array([x[2] for x in ohlcv])
            low = np.array([x[3] for x in ohlcv])
            close = np.array([x[4] for x in ohlcv])

            # Signals

            ## Average Directional Movement Index (ADX)
            adx = talib.ADX(high, low, close, timeperiod=14)
            adx_signal = adx[-1] > 25
            signals += f"A{ adx[-1]:.2f} "

            ## Moving Average Convergence Divergence (MACD)
            macd, macdsignal, macdhist = talib.MACD(
                close, fastperiod=12, slowperiod=26, signalperiod=9
            )
            macd_signal = macd[-1] > macdsignal[-1]
            signals += f"M{macd_signal:1} "

            ## Relative Strength Index (RSI)
            rsi = talib.RSI(close, timeperiod=14)
            signals += f"R{rsi[-1]:.2f} "

            # Decide to buy, sell, or wait
            if (
                (macd_signal and adx_signal and rsi[-1] < 70) or rsi[-1] < 15
            ) and balance_usd < BALANCE:
                if account_balances[QUOTE_CURRENCY]["free"] > balance_usd_diff:
                    if variation < (VARIATION * -3):
                        action, colour = "BUY", "white on red"
                        trading_amount = abs(balance_usd_diff / price)
                else:
                    action, colour = "NO FUNDS", "white on yellow"
            elif (
                (not macd_signal and rsi[-1] > 30) or rsi[-1] > 85
            ) and balance_usd > BALANCE:
                if balance_usd > 10:
                    action, colour = "SELL", "white on green"
                    trading_amount = balance

            if action in ["BUY", "SELL"] and LIVE_TRADE:
                # client.create_post_only_order(
                client.create_limit_order(
                    amount=trading_amount,
                    params=client_params,
                    price=price,
                    side=action.lower(),
                    symbol=symbol,
                    # type="limit",
                )

        table.add_row(
            f"{datetime.now().strftime('%H:%M:%S')}",
            f"{currency}",
            f"{balance_usd:.2f} {QUOTE_CURRENCY}",
            f"{variation:+.2f}%",
            action,
            signals,
            style=colour,
        )

    console.print(table)


# %%
if __name__ == "__main__":
    main()
