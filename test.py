from find_security import load_fno_master
import  pandas as pd
from datetime import datetime, time as dtime
import pytz



SYMBOL = 'ABB'
IST = pytz.timezone("Asia/Kolkata")
today = datetime.now(IST).strftime("%Y-%m-%d")

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





def get_nearest_nifty_fut(df, trade_date):
    futs = df[
        (df["INSTRUMENT"] == "FUTSTK") &
        (df["UNDERLYING_SYMBOL"] == SYMBOL)
    ].copy()


    futs["SM_EXPIRY_DATE"] = pd.to_datetime(futs["SM_EXPIRY_DATE"])
    futs = futs[futs["SM_EXPIRY_DATE"] >= trade_date]

    fut = futs.sort_values("SM_EXPIRY_DATE").iloc[0]
    return fut['SECURITY_ID']




df = load_fno_master()

""" print(get_nearest_nifty_fut(df , today)) """

CErow = find_option_security(df, 7750, "CE", today, SYMBOL)

print(CErow)





