# Foodborne Illness Surveillance & Source Tracing (synthetic demo)

## Run in VS Code
1. Extract this folder and open it in VS Code.
2. Create a virtual environment: `python -m venv .venv`
3. Activate it (Windows PowerShell: `.venv\Scripts\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`).
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `streamlit run app.py`

## Included
- Streamlit dashboard with interactive Plotly charts, filters, person-ID search, source/vendor comparison, rule-based red flags, and CSV/XLSX exports.
- Dedicated **Top 3 suspected sources** tab, ranked using the same transparent heuristic as Overview and exportable to CSV.
- 30 wards in `data/wards_30.csv`; the original `wards.csv` is preserved separately.
- 200 synthetic reports in `data/synthetic_illness_reports.csv`, arranged as five Excel sheets of 40 reports each in `synthetic_surveillance_reports.xlsx`.
- Original supplied CSVs retained in `data/` for source traceability.

## Important accuracy notes
- The linked Google Doc and an `app.py` reference file were not accessible in the available attachments/connectors for this build. The app is based on the supplied CSV schemas and the requirements in the request.
- The supplied wards file contains 24 wards; six clearly labeled synthetic ward rows were added to reach 30. Verify ward names/codes against an official BMC ward list before operational use.
- Generated case reports, daily arrivals, duplicates, isolated cases, late reports, and popular-food decoys are synthetic test fixtures—not real surveillance data. The daily feed is reproducible for a selected date and changes when the selected date changes; it is not connected to a live reporting system.
- Rule-based flags are investigation prompts, not proof of an outbreak, food contamination, or vendor culpability. Confirm through interviews, exposure data, inspections, laboratory testing, and supply-chain records.
- No real patient identifiers should be entered into this demo.


## Integration note for supplied `app.py`
The dashboard keeps the supplied `app.py`'s core investigation concepts (explainable source ranking, date cut-off, duplicate/data-quality review, recorded upstream/downstream tracing, and common entities) and combines them with the synthetic 30-ward, five-sheet demo dataset. The added batch-tracing tab reads `data/supply_chain_events.csv` and displays only recorded links. Scores and flags are triage aids, not causal findings.

## Top 3 suspected sources tab
The tab shows the three highest-ranked vendor/supplier leads for the currently filtered report view, including unique people, distinct reports, affected wards, high/critical reports, onset window, food types, and a CSV export. Ranking weights are unique people 40%, wards affected 25%, high/critical reports 25%, and distinct report IDs 10%. Scores are normalized within the current view and are not probabilities or evidence of causation.

## Run in VS Code (Windows)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
