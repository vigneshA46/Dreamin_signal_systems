import threading
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


# =========================
# Strategy Controller
# =========================
class StrategyController:
    def __init__(self, config):
        self.entry_time = config["entry_time"]
        self.exit_time = config["exit_time"]
        self.no_reentry_after = config["no_reentry_after"]

    def _now(self):
        return datetime.now(IST).time()

    def is_active(self):
        return self._now() >= self._to_time(self.entry_time)

    def should_exit(self):
        return self._now() >= self._to_time(self.exit_time)

    def can_reenter(self):
        if not self.no_reentry_after["enabled"]:
            return True
        return self._now() < self._to_time(self.no_reentry_after["time"])

    def _to_time(self, tstr):
        return datetime.strptime(tstr, "%H:%M").time()


# =========================
# WebSocket Manager
# =========================
class WebSocketManager:
    def __init__(self, client_id, access_token, instruments):
        from dhanhq import marketfeed

        self.feed = marketfeed.DhanFeed(client_id, access_token, instruments, "v2")
        self.subscribers = {}

    def register(self, security_id, leg):
        self.subscribers.setdefault(int(security_id), []).append(leg)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                self.feed.run_forever()
                data = self.feed.get_data()

                if data:
                    self.on_message(data)

            except Exception as e:
                print("WS ERROR:", e)

    def on_message(self, data):
        security_id = int(data["security_id"])

        if security_id in self.subscribers:
            for leg in self.subscribers[security_id]:
                leg.on_tick(data)


# =========================
# Leg Class (Basic)
# =========================
class Leg:
    def __init__(self, leg_config, strategy_controller):
        self.config = leg_config
        self.strategy = strategy_controller

        self.security_id = None  # assigned later

        self.state = {
            "is_open": False,
            "entry_price": None,
        }

    def set_instrument(self, security_id):
        self.security_id = int(security_id)

    def on_tick(self, data):
        ltp = float(data["LTP"])

        if not self.state["is_open"]:
            self.try_entry(ltp)
        else:
            self.manage_trade(ltp)

    def try_entry(self, ltp):
        if not self.strategy.is_active():
            return

        # Only current price entry for now
        if self.config["entry"]["type"] == "current_price":
            print(f"🟢 ENTER LEG {self.config['id']} at {ltp}")

            self.state["is_open"] = True
            self.state["entry_price"] = ltp

    def manage_trade(self, ltp):
        # Placeholder (SL/Target later)
        pass


# =========================
# Instrument Resolver
# =========================
class InstrumentResolver:
    def __init__(self, df, access_token, client_id):
        self.df = df
        self.access_token = access_token
        self.client_id = client_id

    def resolve_leg(self, leg, base_security_id, symbol):
        if leg["market_type"] == "futures":
            from utils.instrument_resolver import get_nearest_nifty_fut

            sec_id = get_nearest_nifty_fut(self.df, datetime.now(), symbol)
            return sec_id

        elif leg["market_type"] == "options":
            from utils.instrument_resolver import fetch_option_chain, find_option_security

            expiry = "NEXT_EXPIRY"  # you will map this properly

            chain = fetch_option_chain(
                base_security_id,
                expiry,
                self.access_token,
                self.client_id
            )

            strike = self._select_strike(chain, leg["strike_type"])

            opt = find_option_security(
                self.df,
                strike,
                leg["option_type"],
                datetime.now(),
                symbol
            )

            return opt["SECURITY_ID"]

    def _select_strike(self, chain, strike_config):
        # placeholder logic
        return 0


# =========================
# Main Engine
# =========================
class PaperTradeEngine:
    def __init__(self, entry_settings, legs, underlying, resolver, ws):
        self.config = entry_settings
        self.legs_config = legs
        self.underlying = underlying
        self.resolver = resolver
        self.ws = ws

        """ self.underlying_id = underlying["security_id"]

        self.global_exit = False

        self.strategy_json = strategy_json
        self.entry_json = entry_json
        self.legs_json = legs_json

        self.df = df
        self.client_id = client_id
        self.access_token = access_token

        self.legs = [] """

    def start(self):
        print("🚀 Starting Paper Trade Engine...")

        # 1. Strategy Controller
        self.strategy = StrategyController(self.entry_json)

        # 2. Resolver
        resolver = InstrumentResolver(
            self.df,
            self.access_token,
            self.client_id
        )

        instruments = []
        base_security_id = self.strategy_json["security_id"]
        symbol = self.strategy_json["symbol"]

        # 3. Create Legs
        for leg_conf in self.legs_json["legs"]:
            leg = Leg(leg_conf, self.strategy)

            sec_id = resolver.resolve_leg(
                leg_conf,
                base_security_id,
                symbol
            )

            leg.set_instrument(sec_id)

            instruments.append((0, sec_id, 15))  # replace with correct constants

            self.legs.append(leg)

        # 4. WebSocket
        self.ws = WebSocketManager(
            self.client_id,
            self.access_token,
            instruments
        )

        # Register legs
        for leg in self.legs:
            self.ws.register(leg.security_id, leg)

        self.ws.start()

        print("✅ Engine running...")
    