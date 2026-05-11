
def option_chain(security_id , expiry):

    oc = dhan.option_chain(
        under_security_id=security,
        under_exchange_segment="IDX_I",
        expiry=expiry 
    )

    option_data = oc["data"]["data"]["oc"]



def get_next_expiry(security_id, index):
    """
    Returns current/next NIFTY expiry date
    directly from Dhan expiry list API
    """

    expiries = dhan.expiry_list(
        under_security_id=security_id,
        under_exchange_segment="IDX_I"
    )

    expiry_list = expiries["data"]

    # first expiry is always nearest expiry
    next_expiry = expiry_list["data"][index]

    return next_expiry




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

