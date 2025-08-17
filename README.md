# Indian Stocks — DCF Fair Value (Polished v4.4)

A Streamlit web app to estimate fair value per share (₹) for Indian stocks using a simple FCFF DCF model.

## Features
- Auto / Manual / Upload modes for financials
- Manual, CAPM (semi-auto), or Full Auto WACC
- Charts: FCFF projection and valuation breakdown
- Downloads: CSV and Excel (with a summary sheet)
- Styling inspired by the attached reference UI (cards, chips, subtle shadows)

## Deploy (Streamlit Cloud)
1. Create a GitHub repo and put these files at the root:
   - `app.py`
   - `dcf.py`
   - `upload_parsers.py`
   - `data_fetchers.py`
   - `requirements.txt`
2. On Streamlit Cloud → New app → choose repo → main file: `app.py`.
3. Push changes any time and hit **Manage app → Restart**.

## Usage
- **Auto mode**: enter a NSE/BSE ticker (e.g. `RELIANCE.NS`, `500325.BO`). We fetch FCFF≈OCF−Capex (₹ Cr), net debt (₹ Cr) and shares (Crore) best-effort via Yahoo.
- **Upload mode**: provide `fcff`, `net_debt`, `shares` (and optionally `current_price`) — or `operating_cash_flow` & `capital_expenditures` to derive FCFF.
- Choose a WACC method and growth assumptions, then click **Run Valuation**.
- Download the projections as CSV or Excel.

> Note: This is an educational tool. Many inputs are approximations or best‑effort; please verify before investment decisions.