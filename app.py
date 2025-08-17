
import streamlit as st
import pandas as pd
import numpy as np

from dcf import run_dcf
from upload_parsers import parse_uploaded_file

# Safe import of optional Yahoo helpers
try:
    import data_fetchers as df
    fetch_from_yfinance = getattr(df, "fetch_from_yfinance", None)
    infer_net_debt_yf = getattr(df, "infer_net_debt_yf", None)
    infer_shares_yf = getattr(df, "infer_shares_yf", None)
    get_current_price_yf = getattr(df, "get_current_price_yf", None)
    auto_wacc_best_effort = getattr(df, "auto_wacc_best_effort", None)
except Exception:
    fetch_from_yfinance = infer_net_debt_yf = infer_shares_yf = get_current_price_yf = auto_wacc_best_effort = None

st.set_page_config(page_title="Indian Stocks — DCF Fair Value (Polished v4.4)", page_icon="📈", layout="wide")

# ------------- Styling (inspired by your screenshot) -------------
st.markdown(
    '''
    <style>
    :root {
        --accent-blue: #2f66f6;
        --chip-purple: #6c4af2;
        --muted: #64748B;
        --card-bg: #ffffff;
        --bg: #f7f8fa;
        --shadow: 0 4px 14px rgba(16,24,40,.08);
        --radius: 14px;
    }
    .main { background: var(--bg); }
    section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #eaeef3; }
    h1, h2, h3 { letter-spacing: .2px; }
    .tt-card {
        background: var(--card-bg);
        border: 1px solid #E9EEF3;
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 18px 18px 10px 18px;
        margin-bottom: 16px;
    }
    .tt-chip {
        display:inline-block; font-size:12px; font-weight:600; color:#fff;
        background: var(--chip-purple); padding:4px 8px; border-radius:10px;
        vertical-align: middle; margin-left:8px;
    }
    .tt-subtle { color: var(--muted); font-size:13px; }
    div[data-testid="stMetricValue"] { font-size: 22px; }
    </style>
    ''',
    unsafe_allow_html=True
)

st.title("📈 Indian Stocks — DCF Fair Value (INR)")
st.caption("Polished v4.4 · Auto/Manual/Upload · Charts · Downloads · Inspired by your reference UI")

# ------------------------ Sidebar ------------------------
st.sidebar.header("1) Mode & Company")
mode = st.sidebar.selectbox("Choose input mode", ["Auto (Yahoo Finance)", "Manual", "Upload (CSV/XLSX)"], index=0)
ticker = st.sidebar.text_input("Ticker (e.g., RELIANCE.NS, TCS.NS)", value="RELIANCE.NS").strip()

st.sidebar.header("2) Growth Path & Terminal")
years = st.sidebar.number_input("Projection years", 3, 15, 10, 1)
g1 = st.sidebar.number_input("Years 1–⌊N/2⌋ CAGR (%)", 0.0, 50.0, 10.0, 0.5)
g2 = st.sidebar.number_input("Years ⌈N/2⌉–N CAGR (%)", 0.0, 50.0, 6.0, 0.5)
gT = st.sidebar.number_input("Terminal growth (%)", 0.0, 10.0, 4.0, 0.25)

st.sidebar.header("3) Discount Rate (WACC)")
wacc_mode = st.sidebar.radio("Mode", ["Manual", "Semi-auto (CAPM)", "Full Auto"])
wacc = None

# ------------- Data containers -------------
fcff_base = None
net_debt = None
shares = None
current_price = None
fin = None

# ------------------------ Data ingest ------------------------
if mode == "Auto (Yahoo Finance)":
    if ticker and fetch_from_yfinance:
        try:
            fin = fetch_from_yfinance(ticker)
            fcff_base = fin.get("fcff", None)
            net_debt = infer_net_debt_yf(fin) if infer_net_debt_yf else None
            shares = infer_shares_yf(fin) if infer_shares_yf else None
            current_price = get_current_price_yf(ticker) if get_current_price_yf else None
            st.markdown('<div class="tt-card tt-subtle">Fetched latest statements via Yahoo Finance.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Yahoo fetch failed: {e}")
    else:
        st.info("Enter a ticker to fetch automatically.")
elif mode == "Upload (CSV/XLSX)":
    up = st.file_uploader("Upload a CSV or Excel file")
    st.caption("Columns accepted: `fcff`, `net_debt`, `shares`, `current_price` or `operating_cash_flow` & `capital_expenditures` (fcff = ocf - capex).")
    if up:
        try:
            parsed = parse_uploaded_file(up)
            fcff_base = parsed.get("fcff")
            net_debt = parsed.get("net_debt")
            shares = parsed.get("shares")
            current_price = parsed.get("current_price")
            st.markdown('<div class="tt-card tt-subtle">Upload parsed successfully.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Upload parse error: {e}")
else:
    st.info("Manual mode enabled — enter base values below.")

# Manual overrides (always visible)
st.markdown('<div class="tt-card">', unsafe_allow_html=True)
st.subheader("Base Inputs")
c1, c2, c3, c4 = st.columns([1,1,1,1])
with c1:
    fcff_base = st.number_input("Base FCFF (₹ Cr)", value=float(fcff_base or 0.0), step=10.0, format="%.2f")
with c2:
    net_debt = st.number_input("Net Debt (₹ Cr)", value=float(0.0 if net_debt is None else net_debt), step=10.0, format="%.2f")
with c3:
    shares = st.number_input("Shares Outstanding (Crore)", value=float(0.0 if shares is None else shares), step=0.01, format="%.4f")
with c4:
    current_price = st.number_input("Current Price (₹) [optional]", value=float(0.0 if current_price is None else current_price), step=1.0, format="%.2f")
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------ WACC handling ------------------------
if wacc_mode == "Manual":
    wacc = st.sidebar.number_input("WACC (%)", 0.0, 50.0, 12.0, 0.25) / 100.0
elif wacc_mode == "Semi-auto (CAPM)":
    rf = st.sidebar.number_input("Risk‑free (%)", 0.0, 20.0, 7.2, 0.1) / 100.0
    beta = st.sidebar.number_input("Beta", 0.0, 3.0, 1.0, 0.05)
    mrp = st.sidebar.number_input("Equity risk premium (%)", 0.0, 20.0, 6.0, 0.1) / 100.0
    kd = st.sidebar.number_input("Pre‑tax cost of debt (%)", 0.0, 30.0, 8.5, 0.1) / 100.0
    tax = st.sidebar.number_input("Tax rate (%)", 0.0, 60.0, 25.0, 0.5) / 100.0
    we = st.sidebar.slider("Equity weight", 0.0, 1.0, 0.8, 0.05)
    wd = 1.0 - we
    ke = rf + beta*mrp
    wacc = we*ke + wd*kd*(1.0 - tax)
else:
    if ticker and auto_wacc_best_effort:
        try:
            auto = auto_wacc_best_effort(ticker, fin if fin else None)
            wacc = auto.get("wacc", None)
            with st.expander("Auto WACC breakdown", expanded=False):
                st.json(auto)
            if wacc is None:
                st.warning("Auto WACC could not be computed; switch to CAPM or Manual.")
        except Exception as e:
            st.error(f"Auto WACC failed: {e}")
    else:
        st.info("Enter a ticker to use Full Auto WACC.")

# ------------------------ Run button ------------------------
run = st.button("Run Valuation")

if run:
    if fcff_base <= 0 or shares <= 0 or wacc is None or wacc <= 0:
        st.error("Please provide positive FCFF, Shares, and WACC.")
    elif gT/100.0 >= wacc:
        st.error("Terminal growth must be less than WACC.")
    else:
        try:
            res = run_dcf(
                fcff=fcff_base,
                net_debt=net_debt or 0.0,
                shares=shares,
                wacc=wacc,
                years=int(years),
                g1=g1/100.0,
                g2=g2/100.0,
                g_terminal=gT/100.0,
            )
            summary = res["summary"]
            df_proj = res["projections"]
            pv_fcff = res["components"]["pv_fcff"]
            pv_tv = res["components"]["pv_terminal"]
            ent = res["components"]["enterprise_value"]
            eq = res["components"]["equity_value"]
            fv = res["components"]["fair_value"]

            st.markdown('<div class="tt-card">', unsafe_allow_html=True)
            st.subheader("Results")
            a,b,c,d = st.columns(4)
            a.metric("Enterprise Value (₹ Cr)", f"{ent:,.2f}")
            b.metric("Equity Value (₹ Cr)", f"{eq:,.2f}")
            c.metric("Fair Value / Share (₹)", f"{fv:,.2f}")
            if current_price and current_price > 0:
                upside = (fv - current_price)/current_price*100.0
                d.metric("Upside vs CMP", f"{upside:.1f}%")
            else:
                d.metric("WACC used", f"{wacc*100:.2f}%")
            st.caption(f"Assumptions: Years={years}, g1={g1:.2f}%, g2={g2:.2f}%, gT={gT:.2f}%")
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- Charts (FCFF path + valuation breakdown) ----
            st.markdown('<div class="tt-card">', unsafe_allow_html=True)
            st.subheader("FCFF Projection")
            st.line_chart(df_proj.set_index("Year")[["FCFF (₹ Cr)"]])
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="tt-card">', unsafe_allow_html=True)
            st.subheader("Valuation Breakdown")
            breakdown = pd.DataFrame({
                "Component": ["PV of FCFF", "PV of Terminal Value", "(-) Net Debt", "Equity Value"],
                "₹ Cr": [pv_fcff, pv_tv, -(net_debt or 0.0), eq],
            })
            st.bar_chart(breakdown.set_index("Component"))
            st.caption("Enterprise Value = PV(FCFF) + PV(Terminal); Equity Value = Enterprise − Net Debt")
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- Data table ----
            st.markdown('<div class="tt-card">', unsafe_allow_html=True)
            st.subheader("Projection Table")
            st.dataframe(df_proj, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- Downloads ----
            from io import BytesIO
            csv = df_proj.to_csv(index=False).encode("utf-8")
            xls_buf = BytesIO()
            with pd.ExcelWriter(xls_buf, engine="openpyxl") as writer:
                df_proj.to_excel(writer, index=False, sheet_name="DCF Projection")
                meta = pd.DataFrame([summary]).T.reset_index()
                meta.columns = ["Metric", "Value"]
                meta.to_excel(writer, index=False, sheet_name="Summary")
            st.download_button("📥 Download CSV", csv, file_name=f"{ticker or 'custom'}_dcf_projection.csv", mime="text/csv")
            st.download_button("📥 Download Excel", xls_buf.getvalue(), file_name=f"{ticker or 'custom'}_dcf_projection.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"DCF run failed: {e}")
else:
    st.markdown('<div class="tt-card tt-subtle">Choose your mode, set growth & WACC, then hit **Run Valuation**.</div>', unsafe_allow_html=True)
