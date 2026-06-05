from fastapi import APIRouter, HTTPException , Request, FastAPI, WebSocket
#from candle_builder import OneMinuteCandleBuilder
import asyncio
from dhanhq import MarketFeed, DhanContext
from dispatcher import publish
from dhan_token import get_access_token
import os
from create_signal_class import PaperEngine

app = FastAPI()
router = APIRouter()

tokens = set()
clients = set()
lock = asyncio.Lock()
engines = {}
symbol_map={}

feed = None
loop = None
restart_lock = asyncio.Lock()

async def connect(ws: WebSocket):
    await ws.accept()
    async with lock:
        clients.add(ws)

async def disconnect(ws: WebSocket):
    async with lock:
        clients.discard(ws)

async def broadcast(data):
    dead = []
    async with lock:
        for c in clients:
            try:
                await c.send_json(data)
            except:
                dead.append(c)

        for d in dead:
            clients.discard(d)

def is_valid_token(token: str):
    return token.isdigit() and len(token) > 3


def on_message(msg):

    token = str(msg.get("security_id"))
    ltp = msg.get("LTP") or msg.get("ltp")

    if not ltp:
        return
    
    publish(token, msg)

    tick = {
        "security_id": token,
        "symbol": symbol_map.get(token),
        "ltp": ltp}
    print("LIVE TICK :", tick)

    for strategy_id, engine in engines.items():

        try:
            engine.on_tick(tick)

        except Exception as e:
    
            print(f"ENGINE ERROR " f"{strategy_id} : {str(e)}")
    """
    try:
        asyncio.run_coroutine_threadsafe(broadcast(msg),loop)

    except Exception as e:
        print("Broadcast error:", e)
    """

def start_dhan_ws():
    global feed

    try:
        access_token = get_access_token()
        client_id = os.getenv("CLIENT_ID")

        dhan_context = DhanContext(client_id, access_token)

        instruments = []

        instruments.append(
            (MarketFeed.IDX, "13", MarketFeed.Quote)
        )

        valid_tokens = []

        for t in list(tokens):
            if is_valid_token(t):
                valid_tokens.append(t)

        instruments.extend([
            (MarketFeed.NSE_FNO, t, MarketFeed.Quote)
            for t in valid_tokens
        ])

        print("Starting WS with:", instruments)

        feed = MarketFeed(
            dhan_context,
            instruments,
            "v2"
        )

        feed.run_forever()

        print("WS CONNECTED")

        while feed is not None:

            try:
                data = feed.get_data()
                token = str(data["security_id"])
                if data:

                    token = str(data["security_id"])
                    """
                    if token not in builders:
                        builders[token] = OneMinuteCandleBuilder()

                    candle = builders[token].process_tick(data)

                    if candle:
                        print("CANDLE:", token, candle)
                    """
                    #print("TICK:", token, data)

                    on_message(data)


            except Exception as e:
                print("DATA ERROR:", e)

    except Exception as e:
        print("WS ERROR:", e)

async def restart_ws():
    global feed

    async with restart_lock:

        feed = None

        await asyncio.sleep(1)
        print("Restarting WS...")

        await asyncio.sleep(5)

        print("Starting new WS...")

        asyncio.get_running_loop().run_in_executor(
            None,
            start_dhan_ws
        )

@router.post("/add-token")
async def add_token(exchange: str, token: str):

    if token in tokens:
        return {"status": "already exists"}

    if not is_valid_token(token):
        return {"error": "Invalid token"}

    async with lock:
        tokens.add(token)

    await restart_ws()

    return {"status": "added", "tokens": list(tokens)}


@router.post("/clear-tokens")
async def clear_tokens():
    async with lock:
        tokens.clear()

    await restart_ws()

    return {"status": "cleared"}

@router.post("/register-engine")
async def register_engine(strategy_id: str, strategy: dict):

    try:

        engine = PaperEngine(
            strategy_id=strategy_id,
            entry_settings=strategy["entry_settings"],
            legs=strategy["legs"],
            underlying=strategy["underlying"]
        )
        engines[strategy_id] = engine

        print(f"ENGINE REGISTERED : {strategy_id}")

        for leg in strategy["legs"]:

            token = str(leg["security_id"])
            tokens.add(token)
            symbol_map[token] = leg["symbol"]

        await restart_ws()

        return {
            "status": "success",
            "strategy_id": strategy_id
        }

    except Exception as e:

        raise HTTPException(status_code=500,detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await connect(ws)

    try:
        while True:
            await ws.receive_text()
    except:
        await disconnect(ws)

@app.on_event("startup")
async def startup():
    global loop
    loop = asyncio.get_running_loop()

    loop.run_in_executor(None, start_dhan_ws)


app.include_router(router)
