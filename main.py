from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from uuid import uuid4
import asyncio
from create_signal_class import PaperEngine
from get_instrument import find_option_instrument

app = FastAPI()

strategies = {}
engines = {}


class StrategyRequest(BaseModel):
    entry_settings: Dict[str, Any]
    config_json: Dict[str, Any]
    index_id: Dict[str, Any]


async def strategy_engine():

    while True:

        try:
            tick = {
                "symbol": "NIFTY",
                "ltp": 24850
            }

            print(f"\nLIVE TICK : {tick}")
            for strategy_id, engine in engines.items():

                print(f"Running Strategy: {strategy_id}")

                engine.on_tick(tick)

            await asyncio.sleep(5)

        except Exception as e:

            print(f"Engine Error: {str(e)}")

            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():

    asyncio.create_task(strategy_engine())

    print("Strategy Engine Started")

@app.post("/create-strategy")
async def create_strategy(request: StrategyRequest):

    strategy_id = str(uuid4())
    data = request.model_dump()
    strategies[strategy_id] = data

    resolved_instruments = find_option_instrument(
    data["config_json"],
    data["index_id"]
    )

    print("RESOLVED:", resolved_instruments)

    engine = PaperEngine(
        entry_settings=data["entry_settings"],
        legs=data["config_json"]["legs"],
        underlying=data["index_id"]["symbol"]
    )
    engines[strategy_id] = engine

    print(f"Strategy Created: {strategy_id}")

    return {
        "status": "success",
        "strategy_id": strategy_id,
        "data": data
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