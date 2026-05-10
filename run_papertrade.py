import json
from engine.paper_engine import PaperTradeEngine
from data.ws_manager import WSManager
from utils.instrument_resolver import InstrumentResolver

# --------------------------
# LOAD STRATEGY JSON
# --------------------------


CLIENT_ID = "1107425275"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc3NTI2MzcwLCJpYXQiOjE3Nzc0Mzk5NzAsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA3NDI1Mjc1In0.ZF_9K3rQM19NAA9Cx-Ug3MFaAhDfH8dfLUko6iVCu75_UHHiqz7yknvggreyRqAR_xTn6Wg58AQiCa_ai1NW-A"


""" with open("strategy.json") as f:
    data = json.load(f)
 """

data = {
    "id": "26b1e32d-5f9a-4397-b9f2-0564d682179e",
    "user_id": "29738b1f-78d7-458f-8007-dd79d282b0d2",
    "entry_settings": {
        "mode": "intraday",
        "momentum": {
            "type": "percentage",
            "value": 50,
            "enabled": true
        },
        "exit_time": "14:51",
        "entry_time": "08:51",
        "positional": {
            "expiry_type": "weekly",
            "exit_days_before_expiry": 0,
            "entry_days_before_expiry": 0
        },
        "delay_restart": {
            "time": null,
            "enabled": false
        },
        "no_reentry_after": {
            "time": "15:51",
            "enabled": true
        }
    },
    "config_json": {
        "legs": [
            {
                "id": 1775287248439,
                "lots": 1,
                "entry": {
                    "type": "current_price",
                    "value": null
                },
                "expiry": "This Week",
                "target": {
                    "type": "mtm",
                    "value": 5000,
                    "enabled": true,
                    "reentry": {
                        "count": 0,
                        "enabled": false
                    }
                },
                "position": "Buy",
                "stoploss": {
                    "type": "mtm",
                    "value": 3000,
                    "enabled": true,
                    "reentry": {
                        "count": 0,
                        "enabled": false
                    }
                },
                "trailing": {
                    "type": "points",
                    "enabled": true,
                    "reentry": {
                        "count": 2,
                        "enabled": true
                    },
                    "tsl_active": 30,
                    "sl_position": 20,
                    "trail_value": 10
                },
                "market_type": "options",
                "option_type": "Call",
                "strike_type": {
                    "type": "atm_spot",
                    "value": "ATM"
                }
            }
        ]
    },
    "status": "published",
    "created_by": "user",
    "created_at": "2026-04-04T01:52:54.309Z",
    "index_id": {
        "symbol": "NIFTY",
        "exchange_id": "NSE",
        "security_id": "13"
    },
    "description": " ccf",
    "startergy_name": "nifty option buying"
}


entry_settings = data["entry_settings"]
legs = data["config_json"]["legs"]
instrument = data["index_id"]

instrument["security_id"] = int(instrument["security_id"])

if instrument["exchange_id"] == "NSE":
    instrument["exchange_id"] = "IDX"

# --------------------------
# INIT RESOLVER
# --------------------------

resolver = InstrumentResolver(
    client_id=CLIENT_ID,
    access_token=ACCESS_TOKEN
)

# --------------------------
# INIT ENGINE
# --------------------------
ws = WSManager(CLIENT_ID, ACCESS_TOKEN)


engine = PaperTradeEngine(
    entry_settings=entry_settings,
    legs=legs,
    underlying=instrument,
    resolver=resolver
    ws=ws
)

# --------------------------
# INIT WEBSOCKET
# --------------------------


# give ws to engine
#engine.ws = ws

# --------------------------
# CONNECT WS → ENGINE
# --------------------------

def on_tick(data):

    tick = {
        "security_id": data["security_id"],
        "ltp": data["last_price"]
    }

    engine.on_tick(tick)

ws.on_message = on_tick

# --------------------------
# SUBSCRIBE UNDERLYING
# --------------------------

ws.subscribe(
    instrument["exchange_id"],
    instrument["security_id"]
)

# --------------------------
# START ENGINE
# --------------------------

print("🚀 Starting Paper Trade Engine...")

ws.start()

# keep process alive
while True:
    pass