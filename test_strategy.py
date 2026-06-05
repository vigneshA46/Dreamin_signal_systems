from create_signal_class import PaperEngine

entry_settings = {
    "entry_time": "09:15",
    "exit_time": "15:15",
    "momentum": {
        "enabled": False,
        "value": 0
    }
}

legs = [

    {
        "id": 1,
        "symbol": "NIFTY25000CE",
        "security_id": "12345",
        "position": "Buy",
        "qty": 75,
        "entry": {
            "type": "current_price"
        },
        "target": {
            "enabled": True,
            "value": 1000
        },
        "stoploss": {
            "enabled": True,
            "value": 500
        },
        "trailing": {
            "enabled": True,
            "type": "mtm",
            "tsl_active": 500,
            "sl_position": 200,
            "trail_value": 100,
            "reentry": {
                "enabled": True,
                "count": 2
            }
        }
    }
]

engine = PaperEngine(
    strategy_id="TEST_1",
    entry_settings=entry_settings,
    legs=legs,
    underlying="NIFTY"
)

ticks = [

    {"symbol": "NIFTY", "ltp": 25000},
    {"symbol": "NIFTY25000CE", "ltp": 100},
    {"symbol": "NIFTY25000CE", "ltp": 110},
    {"symbol": "NIFTY25000CE", "ltp": 120},
    {"symbol": "NIFTY25000CE", "ltp": 140},
    {"symbol": "NIFTY25000CE", "ltp": 160},
    {"symbol": "NIFTY25000CE", "ltp": 130},
    {"symbol": "NIFTY25000CE", "ltp": 90}
]

for tick in ticks:

    print("\n====================")

    print("NEW TICK :", tick)

    engine.on_tick(tick)

print("\nFINAL STATE")

print(engine.state)