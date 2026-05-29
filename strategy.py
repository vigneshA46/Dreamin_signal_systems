from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from uuid import uuid4
from get_instrument import find_option_instrument
from create_signal_class import PaperEngine
from test_api import restart_ws, engines,tokens,symbol_map


app = FastAPI()

strategies = {}


class StrategyRequest(BaseModel):
    entry_settings: Dict[str, Any]
    config_json: Dict[str, Any]
    index_id: Dict[str, Any]


VALID_POSITIONS = ["Buy", "Sell"]
VALID_OPTION_TYPES = ["Call", "Put"]


def validate_strategy(config_json, index_id):

    if "legs" not in config_json:
        raise Exception("legs missing")

    if len(config_json["legs"]) == 0:
        raise Exception("No legs provided")

    validated_legs = []

    for leg in config_json["legs"]:

        if leg["position"] not in VALID_POSITIONS:
            raise Exception("Invalid position")

        if leg["option_type"] not in VALID_OPTION_TYPES:
            raise Exception("Invalid option type")

        if leg["lots"] <= 0:
            raise Exception("Lots should be greater than 0")

        if leg["target"]["enabled"]:

            if leg["target"]["value"] <= 0:
                raise Exception("Invalid target value")

        if leg["stoploss"]["enabled"]:

            if leg["stoploss"]["value"] <= 0:
                raise Exception("Invalid stoploss value")

        validated_legs.append(leg)

    if "symbol" not in index_id:
        raise Exception("Index symbol missing")
    
    return {
        "legs": validated_legs,
        "index": index_id
    }

def normalize_strategy(config_json, index_id):

    normalized_legs = []

    for leg in config_json["legs"]:

        position = leg["position"]

        side = 1 if position == "Buy" else -1

        option_type = leg["option_type"]
        print("OPTION TYPE", option_type)

        option_code = "CE" if option_type == "Call" else "PE"

        expiry = leg["expiry"]

        if expiry == "This Week":

            expiry_index = 0

        elif expiry == "Next Week":

            expiry_index = 1

        else:

            expiry_index = 0

        strike_type = leg["strike_type"]["type"]

        strike_value = leg["strike_type"]["value"]

        qty = leg["lots"] * index_id["lot_size"]
        normalized_leg = {"id": leg["id"],

            "side": side,
            "position": position,
            "option_type": option_code,
            "lots": leg["lots"],
            "qty": qty,
            "market_type": leg["market_type"],
            "entry": leg["entry"],
            "target": leg["target"],
            "stoploss": leg["stoploss"],
            "trailing": leg["trailing"],
            "expiry": expiry,
            "expiry_index": expiry_index,

            "strike_type": {
                "type": strike_type,
                "value": strike_value
            }
        }

        normalized_legs.append(normalized_leg)

    normalized_strategy = {

        "symbol": index_id["symbol"],
        "exchange": index_id["exchange_id"],
        "security_id": index_id["security_id"],
        "lot_size": index_id["lot_size"],
        "legs": normalized_legs
    }

    return normalized_strategy


def build_internal_strategy(strategy_id,entry_settings,normalized_strategy,resolved_instruments):

    strategy_object = {

        "strategy_id": strategy_id,
        "underlying": normalized_strategy["symbol"],
        "exchange": normalized_strategy["exchange"],
        "security_id": normalized_strategy["security_id"],
        "lot_size": normalized_strategy["lot_size"],
        "entry_settings": entry_settings,

        "runtime": {
            "status": "RUNNING",
            "pnl": 0,
            "mtm": 0,
            "positions": [],
            "trades": [],
            "global_exit": False
        },

        "legs": []
    }

    for instrument in resolved_instruments:

        runtime_leg = {

            "id": instrument["id"],
            "symbol": instrument["trading_symbol"],
            "security_id": instrument["security_id"],
            "expiry": instrument["expiry"],
            "strike": instrument["strike"],
            "option_type": instrument["option_type"],
            "position": instrument["position"],
            "side": instrument["side"],
            "qty": instrument["qty"],
            "entry": instrument["entry"],
            "target": instrument["target"],
            "stoploss": instrument["stoploss"],
            "trailing": instrument["trailing"],
            "entry_price": instrument["entry_price"],

            "state": {

                "status": "IDLE",
                "entry_done": False,
                "exit_done": False,
                "current_price": 0,
                "pnl": 0,
                "peak_pnl": 0,
                "trail_sl": None,
                "tsl_active_hit": False,
                "reentry_count": 0,
                "last_exit_reason": None
            }
        }

        strategy_object["legs"].append(runtime_leg)

    return strategy_object

@app.post("/create-strategy")
async def create_strategy(request: StrategyRequest):

    try:

        data = request.model_dump()

        print("RAW REQUEST RECEIVED")
        print(data)

        validated_data = validate_strategy(
            data["config_json"],
            data["index_id"]
        )

        print("\nVALIDATION SUCCESS")

        normalized_data = normalize_strategy(
            data["config_json"],
            data["index_id"]
        )

        print("\nNORMALIZATION SUCCESS")
        strategy_id = str(uuid4())
        resolved_instruments = find_option_instrument(normalized_data, data["index_id"])
        print("RESOLVED INSTRUMENTS")

        print(resolved_instruments)

        internal_strategy = build_internal_strategy(
            strategy_id,
            data["entry_settings"],
            normalized_data,
            resolved_instruments
        )
        strategies[strategy_id] = internal_strategy

        engine = PaperEngine(
            strategy_id=strategy_id,
            entry_settings=data["entry_settings"],
            legs=internal_strategy["legs"],
            underlying=internal_strategy["underlying"])

        engines[strategy_id] = engine
        engine.strategy = internal_strategy
        symbol_map[
        str(internal_strategy["security_id"])] = internal_strategy["underlying"]

        for leg in internal_strategy["legs"]:

            token = str(leg["security_id"])

            tokens.add(token)
            symbol_map[token] = leg["symbol"]
        
        await restart_ws()

        print(f"\nSTRATEGY CREATED : {strategy_id}")

        return {
            "status": "success",
            "strategy_id": strategy_id,
            "data": internal_strategy
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/strategy/{strategy_id}")
async def get_strategy(strategy_id: str):

    strategy = strategies.get(strategy_id)

    if not strategy:

        return {
            "status": "error",
            "message": "Strategy not found"
        }

    return {
        "status": "success",
        "data": strategy
    }