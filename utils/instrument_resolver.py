from dhanhq import dhanhq,DhanContext
import pandas as pd

CLIENT_ID = "1107425275"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc5NTczMDUzLCJpYXQiOjE3Nzk0ODY2NTMsInRva2VuQ29uc3VtZXJUeXBlIjoiQVBQIiwiZGhhbkNsaWVudElkIjoiMTEwNzQyNTI3NSJ9.sM3HeidSWYqMlxsZfujK4JSqMwYDkpjW8-7MwhzGvk4yO-yXeHncPWHbgGocM780WO8g2Jx1JJ1--GNpJIpmcA"

dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
dhan=dhanhq(dhan_context)


def option_chain(security_id, expiry):
    oc = dhan.option_chain(
        under_security_id=int(security_id),
        under_exchange_segment="IDX_I",
        expiry=expiry
    )

    #print("OC", oc) 

    if oc["status"] != "success":
        raise Exception(f"Option Chain API Failed: {oc}")

    return oc["data"]


def get_next_expiry(security_id, index):

    expiries = dhan.expiry_list(
        under_security_id=int(security_id),
        under_exchange_segment="IDX_I"
    )

    #print(expiries)

    if expiries["status"] != "success":
        raise Exception(f"Expiry API Failed: {expiries}")

    expiry_list = expiries["data"]["data"]

    return expiry_list[index]



def find_option_security(df, strike, option_type, trade_date, target_symbol):
    trade_date = pd.to_datetime(trade_date)

    opt = df[ 
        (df["INSTRUMENT"] == "OPTSTK") &
        (df["UNDERLYING_SYMBOL"] == target_symbol) &
        (df["STRIKE_PRICE"] == strike) &
        (df["OPTION_TYPE"] == option_type) &
        (df["SM_EXPIRY_DATE"] >= trade_date)
    ]

    if opt.empty:
        raise ValueError(f"❌ No {option_type} found for strike {strike}")

    return opt.sort_values("SM_EXPIRY_DATE").iloc[0]


def get_nearest_nifty_fut(df, trade_date, symbol):
    futs = df[
        (df["INSTRUMENT"] == "FUTSTK") &
        (df["UNDERLYING_SYMBOL"] == symbol)
    ].copy()


    futs["SM_EXPIRY_DATE"] = pd.to_datetime(futs["SM_EXPIRY_DATE"])
    futs = futs[futs["SM_EXPIRY_DATE"] >= trade_date]

    fut = futs.sort_values("SM_EXPIRY_DATE").iloc[0]
    return fut['SECURITY_ID']

