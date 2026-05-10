
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

