import asyncio
from dhanhq import MarketFeed
from dhanhq import dhanhq,DhanContext
from dhan_token import get_access_token


CLIENT_ID = "1107425275"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzgwMTExMTI0LCJpYXQiOjE3ODAwMjQ3MjQsInRva2VuQ29uc3VtZXJUeXBlIjoiQVBQIiwiZGhhbkNsaWVudElkIjoiMTEwNzQyNTI3NSJ9.JjKLd6wa6YyeQQ1g-nYSNkV2RKI7GQ3RSlEaKq3tOhnlQ11Ud82p9HMcssarsi57nI4j4otL_lTs17ixU-QQIQ"

dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan=dhanhq(dhan_context)


engines = {}


def register_engine(strategy_id, engine):

    engines[strategy_id] = engine
    print(f"ENGINE REGISTERED : {strategy_id}")

def remove_engine(strategy_id):

    if strategy_id in engines:

        del engines[strategy_id]

        print(f"ENGINE REMOVED : {strategy_id}")

def build_subscription_list():

    instruments = []
    added = set()

    for engine in engines.values():

        underlying = (
            MarketFeed.IDX,
            str(engine.strategy["security_id"]),
            MarketFeed.Quote
        )

        if underlying not in added:

            instruments.append(underlying)

            added.add(underlying)

        for leg in engine.strategy["legs"]:

            option = (
                MarketFeed.NSE_FNO,
                str(leg["security_id"]),
                MarketFeed.Quote
            )

            if option not in added:

                instruments.append(option)

                added.add(option)

    return instruments

async def market_feed_loop():

    while True:

        try:

            instruments = build_subscription_list()

            if not instruments:

                await asyncio.sleep(1)

                continue

            print("SUBSCRIBING :", instruments)

            feed = MarketFeed(dhan_context,instruments=instruments,version="v2")

            feed.run_forever()

            while True:

                data = feed.get_data()

                if not data:
                    continue

                tick = {
                    "security_id": str(
                        data.get("security_id")
                    ),

                    "symbol": next(
                            (
                                leg["symbol"]
                                for engine in engines.values()
                                for leg in engine.strategy["legs"]
                                if str(leg["security_id"])== str(data.get("security_id"))),
                                "UNKNOWN"),
                    "ltp": float(data.get("LTP"))
                }

                print("\nLIVE TICK :", tick)

                for strategy_id, engine in engines.items():

                    try:

                        engine.on_tick(tick)

                    except Exception as e:

                        print(
                            f"ENGINE ERROR "
                            f"{strategy_id} : {str(e)}"
                        )

        except Exception as e:

            print("FEED ERROR :", str(e))
            await asyncio.sleep(5)

async def start_market_feed():

    asyncio.create_task(market_feed_loop())

    print("MARKET FEED STARTED")