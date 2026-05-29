from dispatcher import subscribe

positions = {}

def handle_trade(signal):

    strategy_id = signal["strategy_id"]
    action = signal["action"]
    symbol = signal["symbol"]
    qty = signal["qty"]
    price = signal["price"]
    if action == "BUY":
        positions[symbol] = {
            "side": "LONG",
            "qty": qty,
            "entry_price": price
        }
        print(f"BOUGHT {symbol} @ {price}")

    elif action == "SELL":
        positions[symbol] = {
            "side": "SHORT",
            "qty": qty,
            "entry_price": price
        }
        print(f"SOLD {symbol} @ {price}")

    elif action == "EXIT":
        if symbol in positions:
            print(f"EXITED {symbol}")
            del positions[symbol]

subscribe("trade_execution", handle_trade)