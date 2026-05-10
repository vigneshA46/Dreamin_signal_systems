import requests




def select_option_from_chain(chain, leg, underlying_price):

    strike_type = leg["strike_type"]["type"]
    option_type = "ce" if leg["option_type"] == "Call" else "pe"

    oc = chain["data"]["oc"]

    # --------------------------
    # ATM SPOT
    # --------------------------
    if strike_type == "atm_spot":

        atm_strike = min(
            oc.keys(),
            key=lambda x: abs(float(x) - underlying_price)
        )

        selected = oc[str(atm_strike)][option_type]

        return {
            "strike": atm_strike,
            "security_id": selected["security_id"],
            "ltp": selected["last_price"]
        }

    # --------------------------
    # PREMIUM NEAREST
    # --------------------------
    elif strike_type == "premium_nearest":

        target = leg["strike_type"]["value"]

        best = None
        min_diff = float("inf")

        for strike, data in oc.items():
            premium = data[option_type]["last_price"]

            diff = abs(premium - target)

            if diff < min_diff:
                min_diff = diff
                best = (strike, data[option_type])

        return {
            "strike": best[0],
            "security_id": best[1]["security_id"],
            "ltp": best[1]["last_price"]
        }

    # --------------------------
    # DELTA NEAREST
    # --------------------------
    elif strike_type == "delta_nearest":

        target = leg["strike_type"]["value"]

        best = None
        min_diff = float("inf")

        for strike, data in oc.items():
            delta = data[option_type]["greeks"]["delta"]

            diff = abs(delta - target)

            if diff < min_diff:
                min_diff = diff
                best = (strike, data[option_type])

        return {
            "strike": best[0],
            "security_id": best[1]["security_id"],
            "ltp": best[1]["last_price"]
        }

    else:
        raise ValueError("Unsupported strike type")



def fetch_option_chain(security_id, expiry, access_token, client_id):

    url = "https://api.dhan.co/v2/optionchain"

    payload = {
        "UnderlyingScrip": security_id,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }

    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers)

    print(res)
    print(res.json())

    return res.json()


access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc1NDgwMzI4LCJpYXQiOjE3NzUzOTM5MjgsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA3NDI1Mjc1In0.LzD7RVl9s8Q2QtpRhCaN_ROkqXYRGd3G1G3MpQspr8cezQ9Q9PFcvv3Hl0MJ6uwDiTfHJiDfqvUyloGwEwhxQg'

fetch_option_chain(13, '2026-04-07',access_token, '1107425275')
