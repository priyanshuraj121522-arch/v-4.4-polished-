
import pandas as pd
import numpy as np
import yfinance as yf

def pick(df, names):
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            return df.loc[n]
    for n in names:
        if n in df.columns:
            return df[n]
    return None

def fetch_from_yfinance(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = {"error": False, "message": "OK"}
    try:
        cf = t.cashflow
        bs = t.balance_sheet
        is_df = t.income_stmt
        info["cf_df"] = cf
        info["bs_df"] = bs
        info["is_df"] = is_df
        info["info"] = t.info if hasattr(t, "info") else {}
    except Exception as e:
        return {"error": True, "message": f"yfinance statements error: {e}"}

    ocf = pick(cf, ["Total Cash From Operating Activities", "Operating Cash Flow"])
    capex = pick(cf, ["Capital Expenditures", "Capital Expenditure", "CapitalExpenditures"])
    fcff = None
    if ocf is not None and capex is not None:
        try:
            fcff = float(ocf.astype(float).iloc[0] - capex.astype(float).iloc[0]) / 1e7  # ₹ Cr
        except Exception:
            pass
    info["fcff"] = fcff

    total_debt = pick(bs, ["Total Debt"])
    if total_debt is None:
        sd = pick(bs, ["Short/Current Long Term Debt", "Short Term Debt"])
        ld = pick(bs, ["Long Term Debt"])
        td_val = (float(sd.iloc[0]) if sd is not None else 0.0) + (float(ld.iloc[0]) if ld is not None else 0.0)
    else:
        td_val = float(total_debt.iloc[0])
    cash_eq = pick(bs, ["Cash And Cash Equivalents", "Cash"])
    sti = pick(bs, ["Short Term Investments", "Other Short Term Investments"])
    cash_val = float(cash_eq.iloc[0]) if cash_eq is not None else 0.0
    sti_val = float(sti.iloc[0]) if sti is not None else 0.0
    info["net_debt_cr"] = (td_val - (cash_val + sti_val)) / 1e7

    return info

def infer_net_debt_yf(fin: dict):
    return fin.get("net_debt_cr", None)

def infer_shares_yf(fin: dict):
    info = fin.get("info", {}) if isinstance(fin, dict) else {}
    shares = info.get("sharesOutstanding")
    return float(shares) / 1e7 if shares else None  # Crore

def get_current_price_yf(ticker: str):
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="5d", interval="1d")
        if h is not None and not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None

def _try_fetch_india_10y_yield():
    symbols = ["^IN10Y","IN10Y.BOND","IND10Y.BOND","10YIND.BOND","^GSEC10Y","IN10Y:IND"]
    for s in symbols:
        try:
            t = yf.Ticker(s)
            hist = t.history(period="1mo", interval="1d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                last = float(hist["Close"].dropna().iloc[-1])
                return last/100.0 if last > 1.0 else last
        except Exception:
            continue
    return None

def _estimate_beta_vs_nifty(ticker: str, years: int = 2):
    try:
        s = yf.Ticker(ticker).history(period=f"{years}y", interval="1d")["Close"].pct_change().dropna()
        m = yf.Ticker("^NSEI").history(period=f"{years}y", interval="1d")["Close"].pct_change().dropna()
        df = pd.concat([s.rename("s"), m.rename("m")], axis=1).dropna()
        if len(df) < 50:
            return None
        cov = np.cov(df["m"], df["s"])[0,1]
        var_m = np.var(df["m"])
        return cov/var_m if var_m != 0 else None
    except Exception:
        return None

def auto_wacc_best_effort(ticker: str, fin: dict | None = None):
    out = {}
    rf = _try_fetch_india_10y_yield() or 0.072
    beta = _estimate_beta_vs_nifty(ticker) or 1.0
    mrp = 0.06
    kd = 0.085  # fallback
    tax = 0.25

    try:
        t = yf.Ticker(ticker)
        is_df = t.income_stmt
        bs_df = t.balance_sheet
        interest = None
        debt = None
        if is_df is not None and not is_df.empty:
            for c in ["Interest Expense", "Net Interest Income", "Interest Expense Non Operating"]:
                if c in is_df.index:
                    interest = float(is_df.loc[c].iloc[0])
                    break
        if bs_df is not None and not bs_df.empty:
            if "Total Debt" in bs_df.index:
                debt = float(bs_df.loc["Total Debt"].iloc[0])
        if interest and debt and debt > 0:
            kd = abs(interest)/debt
    except Exception:
        pass

    we, wd = 0.8, 0.2
    try:
        info = t.info if 't' in locals() else {}
        mcap = info.get("marketCap")
        if mcap and debt and (mcap + debt) > 0:
            we = mcap/(mcap + debt)
            wd = 1.0 - we
    except Exception:
        pass

    ke = rf + beta*mrp
    wacc = we*ke + wd*kd*(1.0 - tax)

    out.update({"rf": rf, "beta": beta, "mrp": mrp, "kd": kd, "tax_rate": tax, "we": we, "wd": wd, "ke": ke, "wacc": wacc})
    return out
