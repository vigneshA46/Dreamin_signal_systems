import datetime
from zoneinfo import ZoneInfo
from dispatcher import publish

IST = ZoneInfo("Asia/Kolkata")


class PaperEngine:

    def __init__(self,strategy_id, entry_settings, legs, underlying="NIFTY"):
        self.strategy_id = strategy_id
        self.strategy = {"entry_settings": entry_settings,"legs": legs,"underlying": underlying}
        self.config = entry_settings
        self.legs_config = legs
        self.underlying = underlying
        self.global_exit = False

        self.state = {
            "reference_price": None,
            "legs": {},
            "pnl": 0
        }

        self._init_legs()

    def _init_legs(self):
        for leg in self.legs_config:
            self.state["legs"][leg["id"]] = {
                "status": "IDLE",
                "symbol": None,
                "entry_price": None,
                "qty": 0,
                "pnl": 0,
                "peak_pnl": 0,
                "trail_sl": None,
                "tsl_active_hit": False,
                "reentry_count": 0,
                "last_exit_reason": None,

            }

    # --------------------------
    # MAIN LOOP
    # --------------------------

    def on_tick(self, tick):

        if self.global_exit:
            return

        now = datetime.datetime.now(IST).time()

        entry_time = self._parse_time(self.config["entry_time"])
        exit_time = self._parse_time(self.config["exit_time"])

        # WAIT FOR ENTRY TIME
        if now < entry_time:
            return

        # SET REFERENCE PRICE
        if self.state["reference_price"] is None:
            if tick["symbol"] == self.underlying:
                self.state["reference_price"] = tick["ltp"]
                print("Reference Price Set:", tick["ltp"])
            return

        # EXIT ALL AT EXIT TIME
        if now >= exit_time:
            self._exit_all()
            self.global_exit = True
            return

        # MOMENTUM CHECK
        if not self._check_momentum(tick):
            return

        # PROCESS LEGS
        for leg in self.legs_config:
            self._process_leg(leg, tick)

        # UPDATE PNL
        self._update_pnl(tick)

        self._check_overall_pnl()

    # --------------------------
    # MOMENTUM
    # --------------------------

    def _check_momentum(self, tick):

        m = self.config["momentum"]

        if not m["enabled"]:
            return True

        if tick["symbol"] != self.underlying:
            return True

        move = float(tick["ltp"]) - float(self.state["reference_price"])

        return move >= m["value"]

    # --------------------------
    # LEG PROCESSOR
    # --------------------------

    def _process_leg(self, leg, tick):

        leg_state = self.state["legs"][leg["id"]]

        # --------------------------
        # RE-ENTRY LOGIC
        # --------------------------

        if self._check_reentry(leg, leg_state):
            print("RE-ENTERING LEG...")
            self._reset_leg_for_reentry(leg_state)

        # --------------------------
        # NORMAL FLOW
        # --------------------------

        if leg_state["status"] == "IDLE":
            self._try_entry(leg, leg_state, tick)

        elif leg_state["status"] == "OPEN":
            self._check_exit_conditions(leg, leg_state, tick)


    # --------------------------
    # CHECK OVERALL PNL
    # --------------------------

    def _check_overall_pnl(self):

        overall = self.config.get("overall", {})

        if not overall:
            return

        total_pnl = self.state["pnl"]

        # --------------------------
        # TARGET
        # --------------------------

        tgt = overall.get("target", {})

        if tgt.get("enabled"):

            if total_pnl >= tgt.get("value", 0):
                print(f"🎯 OVERALL TARGET HIT: {total_pnl}")
                self._exit_all()
                self.global_exit = True
                return

        # --------------------------
        # STOPLOSS
        # --------------------------

        sl = overall.get("stoploss", {})

        if sl.get("enabled"):

            if total_pnl <= -sl.get("value", 0):
                print(f"🛑 OVERALL SL HIT: {total_pnl}")
                self._exit_all()
                self.global_exit = True
                return


    # --------------------------
    # ENTRY
    # --------------------------

    def _try_entry(self, leg, leg_state, tick):

        if leg["entry"]["type"] != "current_price":
            return

        if tick["symbol"] != leg["symbol"]:
            return

        symbol = leg["symbol"]
        qty = leg["qty"]

        leg_state["status"] = "OPEN"
        leg_state["symbol"] = symbol
        leg_state["qty"] = qty
        leg_state["entry_price"] = float(tick["ltp"])

        #print(f"ENTERED {symbol}")
        signal = {
            "event": "ENTRY",
            "strategy_id": self.strategy_id,
            "symbol": leg["symbol"],
            "security_id": leg["security_id"],
            "side": leg["position"],
            "qty": leg["qty"],
            "price": tick["ltp"]
        }

        publish("trade_execution", signal)
        print("ENTRY SIGNAL :", signal)

    
    # --------------------------
    # TSL
    # --------------------------

    def _handle_trailing(self, leg, leg_state, ltp):

        trailing = leg.get("trailing", {})

        if not trailing.get("enabled"):
            return False  # no exit

        entry = leg_state["entry_price"]
        qty = leg_state["qty"]

        if entry is None:
            return False

        # --------------------------
        # CALCULATE PNL BASED ON TYPE
        # --------------------------

        t_type = trailing.get("type", "mtm")

        if t_type == "points":
            pnl = (ltp - entry) * qty

        elif t_type == "percentage":
            pct = ((ltp - entry) / entry) * 100
            pnl = pct * qty  # normalized

        else:  # mtm
            pnl = (ltp - entry) * qty

        leg_state["pnl"] = pnl

        # --------------------------
        # ACTIVATE TSL
        # --------------------------

        if not leg_state.get("tsl_active_hit"):

            if pnl >= trailing["tsl_active"]:
                leg_state["tsl_active_hit"] = True

                # set initial SL
                leg_state["trail_sl"] = trailing["sl_position"]

                print(f"TSL ACTIVATED → SL = {leg_state['trail_sl']}")

            return False

        # --------------------------
        # UPDATE PEAK
        # --------------------------

        if pnl > leg_state["peak_pnl"]:
            leg_state["peak_pnl"] = pnl

            # move SL forward
            leg_state["trail_sl"] = (
                leg_state["peak_pnl"] - trailing["trail_value"]
            )

            print(f"TSL MOVED → {leg_state['trail_sl']}")

        # --------------------------
        # EXIT CONDITION
        # --------------------------

        if pnl <= leg_state["trail_sl"]:
            print(f"TSL HIT for {leg_state['symbol']}")
            self._exit_leg(leg,leg_state, ltp, "TSL")
            return True

        return False


    # ----------------------------
    # reset legs for reentry
    #-----------------------------

    def _reset_leg_for_reentry(self, leg_state):

        leg_state["status"] = "IDLE"
        leg_state["entry_price"] = None
        leg_state["symbol"] = None

        leg_state["pnl"] = 0
        leg_state["peak_pnl"] = 0
        leg_state["trail_sl"] = None
        leg_state["tsl_active_hit"] = False

        leg_state["reentry_count"] += 1

        print(f"RE-ENTRY COUNT: {leg_state['reentry_count']}")


    #----------------------------
    # check reenetry
    #----------------------------

    def _check_reentry(self, leg, leg_state):

        # must be closed
        if leg_state["status"] != "CLOSED":
            return False

        # config
        reentry_cfg = leg.get("trailing", {}).get("reentry", {})

        if not reentry_cfg.get("enabled"):
            return False

        # count check
        if leg_state["reentry_count"] >= reentry_cfg.get("count", 0):
            return False

        # time restriction
        nr = self.config.get("no_reentry_after", {})

        if nr.get("enabled") and nr.get("time"):
            now = datetime.datetime.now(IST).time()
            cutoff = self._parse_time(nr["time"])

            if now >= cutoff:
                return False

        return True

    # --------------------------
    # EXIT CONDITIONS (SL + TARGET)
    # --------------------------

    def _check_exit_conditions(self, leg, leg_state, tick):

        if tick["symbol"] != leg_state["symbol"]:
            return

        ltp = float(tick["ltp"])
        entry = float(leg_state["entry_price"])
        qty = leg_state["qty"]

        pnl = (ltp - entry) * qty
        leg_state["pnl"] = pnl

        # --------------------------
        # 🔥 TRAILING STOP LOSS
        # --------------------------

        if self._handle_trailing(leg, leg_state, ltp):
            return

        # --------------------------
        # TARGET
        # --------------------------

        if leg["target"]["enabled"]:
            if pnl >= leg["target"]["value"]:
                print(f"TARGET HIT for {leg_state['symbol']}")
                self._exit_leg(leg, leg_state, ltp, "Target HIT")
                return

        # --------------------------
        # STOPLOSS
        # --------------------------

        if leg["stoploss"]["enabled"]:
            if pnl <= -leg["stoploss"]["value"]:
                print(f"SL HIT for {leg_state['symbol']}")
                self._exit_leg(leg, leg_state ,ltp, "SL HIT")
                return
    # --------------------------
    # EXIT LEG
    # --------------------------

    def _exit_leg(self,leg, leg_state, ltp, reason="UNKNOWN"):
        leg_state["status"] = "CLOSED"
        leg_state["last_exit_reason"] = reason

        signal = {
            "event": "EXIT",
            "strategy_id": self.strategy_id,
            "symbol": leg["symbol"],
            "security_id": leg["security_id"],
            "side": "SELL" if leg["position"] == "Buy" else "BUY",
            "qty": leg["qty"],
            "price": ltp,
            "reason": reason
        }

        publish("trade_execution", signal)
        print("EXIT SIGNAL :", signal)
        print(f"EXITED {leg_state['symbol']} | REASON: {reason}")
    
    
    def _exit_all(self):

        print("🚨 EXITING ALL LEGS")

        for leg_state in self.state["legs"].values():
            if leg_state["status"] == "OPEN":
                leg_state["status"] = "CLOSED"
                print(f"FORCE EXIT {leg_state['symbol']}")

                
    # --------------------------
    # PNL UPDATE
    # --------------------------

    def _update_pnl(self, tick):

        total = 0

        for leg_state in self.state["legs"].values():

            if leg_state["status"] != "OPEN":
                continue

            if tick["symbol"] != leg_state["symbol"]:
                continue

            if leg_state["entry_price"] is None:
                continue

            pnl = (float(tick["ltp"]) - leg_state["entry_price"]) * leg_state["qty"]

            leg_state["pnl"] = pnl
            total += pnl

        self.state["pnl"] = total

        print("TOTAL PNL:", total)


    # --------------------------
    # UTILS
    # --------------------------

    def _parse_time(self, t):
        return datetime.datetime.strptime(t, "%H:%M").time()