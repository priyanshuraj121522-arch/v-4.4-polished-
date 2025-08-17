
import pandas as pd

def parse_uploaded_file(file):
    name = getattr(file, "name", "uploaded")
    if str(name).lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    cols = {c.lower().strip(): c for c in df.columns}
    out = {"fcff": None, "net_debt": None, "shares": None, "current_price": None}

    if "fcff" in cols:
        out["fcff"] = float(df[cols["fcff"]].iloc[-1])
    if "net_debt" in cols:
        out["net_debt"] = float(df[cols["net_debt"]].iloc[-1])
    if "shares" in cols or "shares_outstanding" in cols:
        key = cols.get("shares") or cols.get("shares_outstanding")
        out["shares"] = float(df[key].iloc[-1])
    if "current_price" in cols:
        out["current_price"] = float(df[cols["current_price"]].iloc[-1])

    if out["fcff"] is None and "operating_cash_flow" in cols and "capital_expenditures" in cols:
        ocf = float(df[cols["operating_cash_flow"]].iloc[-1])
        capex = float(df[cols["capital_expenditures"]].iloc[-1])
        out["fcff"] = ocf - capex

    if out["fcff"] is None:
        raise ValueError("Could not find or derive FCFF. Provide fcff or (operating_cash_flow & capital_expenditures).")

    return out
