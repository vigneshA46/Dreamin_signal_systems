from utils.instrument_resolver import dhan,get_next_expiry, option_chain

"""
#print(dhan.get_fund_limits())
config_json={
  "legs": [
    {
      "id": 1778407949157,
      "lots": 1,
      "entry": {
        "type": "current_price",
        "value": None
      },
      "expiry": "This Week",
      "target": {
        "type": "mtm",
        "value": 4000,
        "enabled": True,
        "reentry": {
          "count": 0,
          "enabled": False
        }
      },
      "position": "Buy",
      "stoploss": {
        "type": "mtm",
        "value": 2000,
        "enabled": True,
        "reentry": {
          "count": 0,
          "enabled": False
        }
      },
      "trailing": {
        "type": "mtm",
        "enabled": True,
        "reentry": {
          "count": 3,
          "enabled": True
        },
        "tsl_active": 2000,
        "sl_position": 1000,
        "trail_value": 500
      },
      "market_type": "options",
      "option_type": "Call",
      "strike_type": {
        "type": "atm_spot",
        "value": "ATM"
      }
    },
    {
      "id": 1778408206992,
      "lots": 1,
      "entry": {
        "type": "current_price",
        "value": None
      },
      "expiry": "This Week",
      "target": {
        "type": "mtm",
        "value": 4000,
        "enabled": True,
        "reentry": {
          "count": 0,
          "enabled": False
        }
      },
      "position": "Buy",
      "stoploss": {
        "type": "mtm",
        "value": 2000,
        "enabled": True,
        "reentry": {
          "count": 0,
          "enabled": False
        }
      },
      "trailing": {
        "type": "mtm",
        "enabled": True,
        "reentry": {
          "count": 3,
          "enabled": True
        },
        "tsl_active": 2000,
        "sl_position": 1000,
        "trail_value": 500
      },
      "market_type": "options",
      "option_type": "Put",
      "strike_type": {
        "type": "premium_nearest",
        "value": "20"
      }
    }
  ]
}

index_id ={
  "symbol": "NIFTY",
  "lot_size": 65,
  "exchange_id": "NSE",
  "security_id": "13"
}
"""

def find_option_instrument(config_json, index_id):

    security_id = index_id["security_id"]

    final_instruments = []
    expiry_cache = {}
    option_chain_cache = {}
    ticker = dhan.ticker_data(
    securities={
        "IDX_I": [int(security_id)]
        }
    )

    print("TICKER:", ticker)

    if ticker["status"] != "success":
        raise Exception(f"Ticker API Failed: {ticker}")

    spot_price = float(
        ticker["data"]["data"]["IDX_I"][index_id["security_id"]]["last_price"]
    )

    print("SPOT PRICE:", spot_price)

    for leg in config_json["legs"]:

        expiry_type = leg["expiry"]

        if expiry_type == "This Week":
            expiry_index = 0

        elif expiry_type == "Next Week":
            expiry_index = 1

        else:
            expiry_index = 0

        if expiry_index not in expiry_cache:

            expiry_cache[expiry_index] = get_next_expiry(
                security_id=security_id,
                index=expiry_index
            )

        expiry = expiry_cache[expiry_index]

        if expiry not in option_chain_cache:

            option_chain_cache[expiry] = option_chain(
                security_id=security_id,
                expiry=expiry
            )

        oc_response = option_chain_cache[expiry]

        oc_data = oc_response["data"]["oc"]

        option_type = leg["option_type"]
        strike_type = leg["strike_type"]["type"]
        strike_value = leg["strike_type"]["value"]

        strike_list = sorted(
            [int(float(strike)) for strike in oc_data.keys()]
        )

        #security_id = str(index_id["security_id"])

        nearest_diff = float("inf")
        atm_strike = None

        for strike in strike_list:

            diff = abs(strike - spot_price)

            if diff < nearest_diff:

                nearest_diff = diff
                atm_strike = strike

        selected_strike = atm_strike

        if strike_type == "atm_spot":

            selected_strike = atm_strike

        elif strike_type == "otm_points":

            points = int(strike_value) if str(strike_value).isdigit() else 0

            if option_type == "Call":
                selected_strike = atm_strike + points

            else:
                selected_strike = atm_strike - points

        elif strike_type == "itm_points":

            points = int(strike_value) if str(strike_value).isdigit() else 0

            if option_type == "Call":
                selected_strike = atm_strike - points

            else:
                selected_strike = atm_strike + points

        elif strike_type == "premium_nearest":

            target_premium = float(strike_value)

            nearest_diff = float("inf")

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                premium = float(option_data["last_price"])

                diff = abs(premium - target_premium)

                if diff < nearest_diff:

                    nearest_diff = diff
                    selected_strike = int(float(strike_key_loop))

        elif strike_type == "premium_lt":

            target_premium = float(strike_value)

            valid_strikes = []

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                premium = float(option_data["last_price"])

                if premium < target_premium:

                    valid_strikes.append(
                        (
                            abs(premium - target_premium),
                            int(float(strike_key_loop))
                        )
                    )

            if valid_strikes:
                selected_strike = min(valid_strikes)[1]

        elif strike_type == "premium_gt":

            target_premium = float(strike_value)

            valid_strikes = []

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                premium = float(option_data["last_price"])

                if premium > target_premium:

                    valid_strikes.append(
                        (
                            abs(premium - target_premium),
                            int(float(strike_key_loop))
                        )
                    )

            if valid_strikes:
                selected_strike = min(valid_strikes)[1]

        elif strike_type == "delta_nearest":

            target_delta = abs(float(strike_value))

            nearest_diff = float("inf")

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                delta = abs(float(option_data["greeks"]["delta"]))

                diff = abs(delta - target_delta)

                if diff < nearest_diff:

                    nearest_diff = diff
                    selected_strike = int(float(strike_key_loop))

        elif strike_type == "delta_lt":

            target_delta = abs(float(strike_value))

            valid_strikes = []

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                delta = abs(float(option_data["greeks"]["delta"]))

                if delta < target_delta:

                    valid_strikes.append(
                        (
                            abs(delta - target_delta),
                            int(float(strike_key_loop))
                        )
                    )

            if valid_strikes:
                selected_strike = min(valid_strikes)[1]

        elif strike_type == "delta_gt":

            target_delta = abs(float(strike_value))

            valid_strikes = []

            for strike_key_loop, data in oc_data.items():

                option_data = data["ce"] if option_type == "Call" else data["pe"]

                delta = abs(float(option_data["greeks"]["delta"]))

                if delta > target_delta:

                    valid_strikes.append(
                        (
                            abs(delta - target_delta),
                            int(float(strike_key_loop))
                        )
                    )

            if valid_strikes:
                selected_strike = min(valid_strikes)[1]

        strike_key = f"{float(selected_strike):.6f}"

        if strike_key not in oc_data:
            raise Exception(f"Strike {selected_strike} not found in option chain")

        strike_data = oc_data[strike_key]
        #print("ATM STRIKE:", atm_strike)
        #print("SELECTED STRIKE:", selected_strike)
        #print("STRIKE DATA:", strike_data)

        if option_type == "Call":

            if "ce" not in strike_data:
                raise Exception(f"CE data missing for strike {selected_strike}")

            instrument = strike_data["ce"]

        else:

            if "pe" not in strike_data:
                raise Exception(f"PE data missing for strike {selected_strike}")

            instrument = strike_data["pe"]

        final_instruments.append({
            "security_id": instrument["security_id"],
            "expiry": expiry,
            "strike": selected_strike,
            "option_type": option_type
        })

    return final_instruments


#result = find_option_instrument(config_json, index_id)

#print(result)
#print(dir(dhan))
