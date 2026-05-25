from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from uuid import uuid4

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
        strategies[strategy_id] = validated_data

        print(f"\nSTRATEGY CREATED : {strategy_id}")

        return {
            "status": "success",
            "strategy_id": strategy_id,
            "data": normalized_data
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