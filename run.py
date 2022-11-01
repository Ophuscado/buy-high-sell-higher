#!.venv/bin/python

"""
Buy High, Sell Higher (BETA)

This script will attempt to profit buying low and selling high on FTX.
"""

import os
from datetime import datetime

import ccxt
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track
from rich.table import Table

load_dotenv()

# Configuration
BALANCE = int(os.environ["BALANCE"])
CURRENCIES = os.environ["CURRENCIES"].split()
LIVE_MODE = os.environ["LIVE_MODE"] == "True"
REFERENCE = "USD"
VARIATION = float(os.environ["VARIATION_%"])

## Exchange authentication
client = ccxt.ftx()
client.apiKey = os.environ["FTX_PUBLIC_KEY"]
client.secret = os.environ["FTX_SECRET_KEY"]
client_params = {"subaccount": os.environ["FTX_SUBACCOUNT"]}
balances = client.fetch_balance(params=client_params)

# UI
console = Console()
table = Table(title="Buy High, Sell Higher (BETA)")
table.add_column("Datetime")
table.add_column("Action")
table.add_column("Trading pair")
table.add_column("Balance")
table.add_column("Variation")
table.add_column("Amount")
table.add_column("Price")
table.add_column("High (24h)")
table.add_column("Low (24h)")
table.add_column("Volume (24h)")


def main():
    """Main function."""
    if LIVE_MODE:
        client.cancel_all_orders(params=client_params)

    for _, currency in track(enumerate(CURRENCIES), description="Processing..."):
        action, colour = "HODL", "white"
        symbol = f"{currency}/{REFERENCE}"
        ticker = client.fetch_ticker(symbol)

        price = ticker.get("last")
        balance = round((balances.get("total").get(currency) or 0) * price, 2)
        balance_diff = round(balance - BALANCE, 2)
        trade_amount = abs(
            float(client.amount_to_precision(symbol, (balance_diff) / price))
        )
        variation = round((balance_diff) / BALANCE * 100, 2)

        if abs(variation) >= VARIATION:
            if balance > BALANCE:
                action, colour = "SELL", "green"
                if LIVE_MODE:
                    client.create_limit_sell_order(
                        symbol=symbol,
                        amount=trade_amount,
                        price=price,
                        params=client_params,
                    )

            elif balance < BALANCE:
                if balances.get("free").get(REFERENCE) >= (trade_amount * price):
                    action, colour = "BUY", "red"
                    if LIVE_MODE:
                        client.create_limit_buy_order(
                            symbol=symbol,
                            amount=trade_amount,
                            price=price,
                            params=client_params,
                        )

                else:
                    action, colour = "NO FUNDS", "yellow"

        table.add_row(
            str(datetime.now()),
            symbol,
            action,
            f"{balance} {REFERENCE}",
            f"{balance_diff} {REFERENCE} ({variation}%)",
            f"{trade_amount} {currency}",
            f"{ticker.get('last')} {REFERENCE}",
            f"{ticker.get('info').get('priceHigh24h')} {REFERENCE}",
            f"{ticker.get('info').get('priceLow24h')} {REFERENCE}",
            f"{float(ticker.get('info').get('volumeUsd24h')):,} {REFERENCE}",
            style=colour,
        )

    console.print(table)


if __name__ == "__main__":
    main()
