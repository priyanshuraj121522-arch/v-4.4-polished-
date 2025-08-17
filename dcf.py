
import pandas as pd

def run_dcf(fcff: float, net_debt: float, shares: float, wacc: float,
            years: int = 10, g1: float = 0.08, g2: float = 0.05, g_terminal: float = 0.04):
    if fcff is None or fcff <= 0:
        raise ValueError("FCFF must be positive")
    if shares is None or shares <= 0:
        raise ValueError("Shares must be positive")
    if wacc is None or wacc <= 0:
        raise ValueError("WACC must be positive")
    if g_terminal >= wacc:
        raise ValueError("Terminal growth must be less than WACC")

    n1 = years // 2
    n2 = years - n1

    proj = []
    level = fcff
    for _ in range(n1):
        level *= (1.0 + g1)
        proj.append(level)
    for _ in range(n2):
        level *= (1.0 + g2)
        proj.append(level)

    disc_factors = [1.0/((1.0 + wacc)**t) for t in range(1, years+1)]
    pv_fcff = sum(cf * df for cf, df in zip(proj, disc_factors))

    tv = proj[-1] * (1.0 + g_terminal) / (wacc - g_terminal)
    pv_tv = tv * disc_factors[-1]

    enterprise_value = pv_fcff + pv_tv
    equity_value = enterprise_value - (net_debt or 0.0)
    fair_value = equity_value / shares

    df = pd.DataFrame({
        "Year": list(range(1, years+1)),
        "FCFF (₹ Cr)": proj,
        "Discount Factor": disc_factors,
        "PV of FCFF (₹ Cr)": [proj[i] * disc_factors[i] for i in range(years)]
    })

    summary = {
        "Enterprise Value (₹ Cr)": round(enterprise_value, 2),
        "Equity Value (₹ Cr)": round(equity_value, 2),
        "Fair Value / Share (₹)": round(fair_value, 2),
        "Assumptions": {
            "Years": years,
            "g1": g1,
            "g2": g2,
            "g_terminal": g_terminal,
            "WACC": wacc,
        }
    }

    return {
        "summary": summary,
        "projections": df,
        "components": {
            "pv_fcff": pv_fcff,
            "pv_terminal": pv_tv,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "fair_value": fair_value,
        }
    }
