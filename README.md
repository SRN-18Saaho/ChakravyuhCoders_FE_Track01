# Chakravyuh Coders — Foodborne Outbreak Prototype

A beginner-friendly Streamlit prototype using **fictional synthetic data**. It demonstrates data-quality checks, a transparent batch-ranking heuristic, time-filtered reports, Plotly charts, NetworkX supply-chain tracing in both directions, and detection of entities shared across multiple batch paths.

> Safety and validity note: this is a hackathon learning prototype. Its score is not a probability and does not establish that any food is contaminated. The included records are fictional and must not be presented as real public-health evidence.

## Files

- `app.py` — main Streamlit application; uses pandas, NetworkX and Plotly.
- `generate_demo_data.py` — writes reproducible fictional CSV examples.
- `data/illness_reports.csv` — example illness/exposure reports.
- `data/supply_chain.csv` — example batch/supplier links.
- `bayesian_demo.py` — isolated teaching example for Bayes' theorem using invented values; not part of the app's ranking.
- `requirements.txt` — Python packages to install.

## Recommended tools

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ .
2. Install Visual Studio Code from https://code.visualstudio.com/ and add Microsoft's Python extension.
3. Open this folder in VS Code.

Python is usually run through a **Python interpreter**, not a traditional compiler such as the one used for C/C++. VS Code is the editor; Python is the interpreter/runtime.

## Run on Windows (easiest method)

1. Extract the ZIP file first; do not run the app from inside the ZIP preview.
2. Open the extracted `chakravyuh_food_traceability_starter` folder.
3. Double-click `run_app_windows.bat`. The first run creates a local Python environment and installs required packages, so an internet connection is needed.
4. Keep the black terminal window open while using the dashboard. The app should open in your browser.

If the launcher fails, follow the manual steps below.

## Run on Windows manually (PowerShell or Command Prompt)

From this project folder:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

If you are using a terminal where the `py` launcher is unavailable, try `python` in its place. Open the local URL Streamlit prints (usually `http://localhost:8501`).

## Run on macOS/Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Regenerate the synthetic CSV files

```bash
python generate_demo_data.py
```

The script writes the CSV files into `data/`. It uses fixed, hand-authored example rows, so the output is repeatable.

## CSV columns expected by the app

### illness_reports.csv

`report_id, patient_id, report_date, onset_date, ward, food_item, outlet_id, batch_id`

Dates should be parseable by pandas, ideally `YYYY-MM-DD`. Some blank fields are deliberately included to demonstrate data-quality warnings.

### supply_chain.csv

`batch_id, source, target, relationship`

Each row represents a directed relationship for a batch, for example a batch moving to a wholesaler and then to a vendor or outlet.

## What to try in the demo

1. Launch the app with no uploaded files to use the included sample data.
2. Move the “Analyse reports received up to” date backwards and forwards to see the as-of view change.
3. Review the possible duplicate and missing-field warnings.
4. Compare batch ranking and select a batch to view its supply-chain graph.
5. Upload your own CSV files using the same column names to test the workflow.
6. Select an entity in a batch path to inspect its recorded upstream suppliers and downstream recipients.
7. Review **Common-source detection** for suppliers/entities appearing in multiple batch paths. Treat these as leads to verify, not confirmed causes.

## Current limitations

- Ranking weights are illustrative and should be documented, tested and calibrated before any real use.
- A list of reported cases alone cannot reliably estimate risk without appropriate comparison data and independent evidence.
- The graph only shows the supply-chain relationships provided in the input CSV; upstream/downstream tracing cannot discover links that are missing from the data.
- Common-source detection finds entities shared across batch paths, but does not prove that the entity supplied the relevant food during the exposure window or caused illness.
- The as-of date filter uses report receipt date and excludes reports received later than the selected date; supply-chain edges themselves have no timestamps in this starter schema.
- The app does not connect to live MCGM, hospital or NCDC systems; no external API is used.
- `bayesian_demo.py` is separate from the main application and uses a made-up likelihood ratio solely to teach the calculation.
