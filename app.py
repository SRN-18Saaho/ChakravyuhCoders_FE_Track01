"""Chakravyuh Coders: synthetic foodborne-outbreak triage prototype.

This is an educational demo only. Its scores are investigation-priority
heuristics, not probabilities and not proof that food is contaminated.
"""
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_COLUMNS = ["report_id", "patient_id", "report_date", "onset_date", "ward", "food_item", "outlet_id", "batch_id"]
CHAIN_COLUMNS = ["batch_id", "source", "target", "relationship"]

st.set_page_config(page_title="Chakravyuh | Food Traceability", page_icon="🧪", layout="wide")
st.title("Chakravyuh Coders: Foodborne Outbreak Investigation")
st.caption("Synthetic-data prototype • Local processing • No external API required")
st.warning(
    "Educational prototype only. A high score is a lead for investigation, not a diagnosis or proof of contamination. "
    "All included sample records are fictional."
)


def read_csv_source(uploaded_file, fallback_path: Path) -> pd.DataFrame:
    """Read an uploaded CSV, or use the included sample CSV when none is uploaded."""
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    if not fallback_path.exists():
        st.error(f"Could not find {fallback_path.name}. Run generate_demo_data.py first.")
        st.stop()
    return pd.read_csv(fallback_path)


def check_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        st.error(f"{label} is missing required columns: {', '.join(missing)}")
        st.stop()


def standardise_text_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Trim text and convert empty strings to missing values without altering IDs otherwise."""
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()
            df[column] = df[column].replace("", pd.NA)
    return df


def create_batch_ranking(reports: pd.DataFrame) -> pd.DataFrame:
    """Build an explainable heuristic score on a 0-100 scale; this is not a probability."""
    usable = reports.dropna(subset=["batch_id"]).copy()
    if usable.empty:
        return pd.DataFrame(columns=["batch_id", "unique_patients", "outlets", "wards", "priority_score"])

    ranking = usable.groupby("batch_id", dropna=True).agg(
        unique_patients=("patient_id", "nunique"),
        outlets=("outlet_id", "nunique"),
        wards=("ward", "nunique"),
        reports=("report_id", "nunique"),
    ).reset_index()

    # These weights are illustrative defaults, not epidemiologically validated.
    weights = {"unique_patients": 0.65, "outlets": 0.20, "wards": 0.15}
    score = pd.Series(0.0, index=ranking.index)
    for column, weight in weights.items():
        maximum = ranking[column].max()
        if pd.notna(maximum) and maximum > 0:
            score = score + (ranking[column] / maximum) * weight
    ranking["priority_score"] = (score * 100).round(1)
    return ranking.sort_values(["priority_score", "unique_patients"], ascending=False)


def make_network_figure(chain_for_batch: pd.DataFrame) -> go.Figure | None:
    """Render a single batch's traceability graph using NetworkX + Plotly."""
    if chain_for_batch.empty:
        return None

    graph = nx.DiGraph()
    for row in chain_for_batch.itertuples(index=False):
        graph.add_edge(row.source, row.target, relationship=row.relationship)

    positions = nx.spring_layout(graph, seed=42)
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=2, color="#8b93a7"),
        hoverinfo="none", name="Supply-chain links"
    ))

    node_x, node_y, labels, hover = [], [], [], []
    for node in graph.nodes():
        x, y = positions[node]
        node_x.append(x)
        node_y.append(y)
        labels.append(node)
        hover.append(f"Entity: {node}<br>Batch: {chain_for_batch['batch_id'].iloc[0]}")

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=labels, textposition="top center", hovertext=hover,
        hoverinfo="text", name="Supply-chain entities",
        marker=dict(size=22, line=dict(width=1, color="#ffffff"))
    ))
    fig.update_layout(
        title="Supply-chain path for selected batch",
        showlegend=False, height=480,
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def build_batch_graph(chain_for_batch: pd.DataFrame) -> nx.DiGraph:
    """Build a directed graph from the recorded links for one batch."""
    graph = nx.DiGraph()
    for row in chain_for_batch.itertuples(index=False):
        graph.add_edge(row.source, row.target, relationship=row.relationship)
    return graph


def find_common_entities(chain: pd.DataFrame) -> pd.DataFrame:
    """Find entities linked to multiple batches; these are leads, not proof of a common cause."""
    rows = []
    valid_chain = chain.dropna(subset=["batch_id", "source", "target"]).copy()
    for batch_id, batch_edges in valid_chain.groupby("batch_id"):
        entities = set(batch_edges["source"].astype(str)) | set(batch_edges["target"].astype(str))
        for entity in entities:
            rows.append({"entity": entity, "batch_id": str(batch_id)})
    if not rows:
        return pd.DataFrame(columns=["entity", "batch_count", "batch_ids"])
    entity_batches = pd.DataFrame(rows).drop_duplicates()
    common = entity_batches.groupby("entity").agg(
        batch_count=("batch_id", "nunique"),
        batch_ids=("batch_id", lambda values: ", ".join(sorted(values))),
    ).reset_index()
    return common.loc[common["batch_count"] > 1].sort_values(
        ["batch_count", "entity"], ascending=[False, True]
    )


st.sidebar.header("Data inputs")
reports_upload = st.sidebar.file_uploader("Upload illness reports CSV (optional)", type=["csv"], key="reports")
chain_upload = st.sidebar.file_uploader("Upload supply-chain CSV (optional)", type=["csv"], key="chain")
st.sidebar.caption("Leave uploads empty to use the included fictional demo data.")

reports_raw = read_csv_source(reports_upload, DATA_DIR / "illness_reports.csv")
chain_raw = read_csv_source(chain_upload, DATA_DIR / "supply_chain.csv")
check_columns(reports_raw, REPORT_COLUMNS, "Illness reports CSV")
check_columns(chain_raw, CHAIN_COLUMNS, "Supply-chain CSV")

reports = standardise_text_columns(reports_raw, ["report_id", "patient_id", "ward", "food_item", "outlet_id", "batch_id"])
chain = standardise_text_columns(chain_raw, ["batch_id", "source", "target", "relationship"])
reports["report_date"] = pd.to_datetime(reports["report_date"], errors="coerce")
reports["onset_date"] = pd.to_datetime(reports["onset_date"], errors="coerce")

# Identify exact repeated report IDs and possible repeated patient/exposure combinations.
repeated_report_ids = int(reports["report_id"].duplicated(keep=False).sum())
possible_duplicate_rows = pd.Series(False, index=reports.index)
if {"patient_id", "onset_date", "food_item"}.issubset(reports.columns):
    possible_duplicate_rows = reports.duplicated(subset=["patient_id", "onset_date", "food_item"], keep=False)
    # Do not count blank patient IDs as duplicate evidence.
    possible_duplicate_rows = possible_duplicate_rows & reports["patient_id"].notna()

missing_counts = reports[REPORT_COLUMNS].isna().sum()

valid_dates = reports["report_date"].dropna()
if valid_dates.empty:
    st.error("No valid report_date values were found. Check the CSV date format (for example, YYYY-MM-DD).")
    st.stop()

latest_date = valid_dates.max().date()
cutoff = st.sidebar.date_input("Analyse reports received up to", value=latest_date)
analysis_reports = reports.loc[reports["report_date"].dt.date <= cutoff].copy()
# An exact duplicated report ID is counted once in downstream summaries.
analysis_reports = analysis_reports.drop_duplicates(subset=["report_id"], keep="first")

st.subheader("Data quality checks")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Rows available by date", len(analysis_reports))
q2.metric("Rows with possible duplicate exposure", int(possible_duplicate_rows.sum()))
q3.metric("Rows missing a batch ID", int(analysis_reports["batch_id"].isna().sum()))
q4.metric("Rows missing a ward", int(analysis_reports["ward"].isna().sum()))
if repeated_report_ids:
    st.warning(f"{repeated_report_ids} rows share a repeated report_id. Downstream summaries retain the first row for each ID.")
if possible_duplicate_rows.any():
    with st.expander("Inspect possible duplicate patient/exposure reports"):
        st.dataframe(reports.loc[possible_duplicate_rows, REPORT_COLUMNS], use_container_width=True)
with st.expander("Missing values by column"):
    st.dataframe(missing_counts.rename("missing values").to_frame(), use_container_width=True)

st.subheader("Source ranking")
ranking = create_batch_ranking(analysis_reports)
if ranking.empty:
    st.info("No reports with a batch ID are available at this analysis date.")
else:
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("**Potential leads (heuristic priority score)**")
        st.dataframe(ranking, use_container_width=True, hide_index=True)
        st.caption("Score uses illustrative weights: 65% unique patients, 20% distinct outlets, 15% distinct wards, each normalised against the highest value in this dataset. It is not a probability.")
    with right:
        chart = px.bar(
            ranking.sort_values("priority_score", ascending=True),
            x="priority_score", y="batch_id", orientation="h",
            labels={"priority_score": "Heuristic priority score (0–100)", "batch_id": "Batch"},
            title="Relative investigation priority",
            hover_data=["unique_patients", "outlets", "wards", "reports"],
        )
        chart.update_layout(height=380, margin=dict(l=10, r=15, t=55, b=20))
        st.plotly_chart(chart, use_container_width=True)

st.subheader("Reports over time")
time_data = analysis_reports.dropna(subset=["report_date"]).groupby(analysis_reports["report_date"].dt.date).agg(
    reports=("report_id", "nunique")
).reset_index(names="report_date")
if not time_data.empty:
    time_chart = px.line(time_data, x="report_date", y="reports", markers=True,
                         labels={"report_date": "Report date", "reports": "Distinct report IDs"},
                         title="Reports received by date")
    st.plotly_chart(time_chart, use_container_width=True)
else:
    st.info("No dated reports available for this cutoff.")

st.subheader("Supply-chain tracing")
known_batches = sorted(set(analysis_reports["batch_id"].dropna().astype(str)) & set(chain["batch_id"].dropna().astype(str)))
if known_batches:
    selected_batch = st.selectbox("Select a batch to trace", known_batches)
    batch_edges = chain.loc[chain["batch_id"].astype("string") == selected_batch].copy()
    graph = build_batch_graph(batch_edges)
    fig = make_network_figure(batch_edges)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(batch_edges, use_container_width=True, hide_index=True)

        entities = sorted(str(node) for node in graph.nodes())
        selected_entity = st.selectbox(
            "Explore connections from an entity",
            entities,
            help="Upstream means recorded suppliers before this entity; downstream means recorded recipients after it."
        )
        upstream = sorted(str(node) for node in nx.ancestors(graph, selected_entity))
        downstream = sorted(str(node) for node in nx.descendants(graph, selected_entity))
        trace_left, trace_right = st.columns(2)
        with trace_left:
            st.markdown(f"**Upstream of {selected_entity}**")
            if upstream:
                st.write(" → ".join(upstream))
            else:
                st.caption("No upstream links are recorded for this entity in the selected batch.")
        with trace_right:
            st.markdown(f"**Downstream of {selected_entity}**")
            if downstream:
                st.write(" → ".join(downstream))
            else:
                st.caption("No downstream links are recorded for this entity in the selected batch.")
    else:
        st.info("No supply-chain links are recorded for this batch.")
else:
    st.info("No batch IDs overlap between the reports and supply-chain records.")

st.subheader("Common-source detection")
st.caption(
    "Looks for suppliers or other entities that appear in the recorded paths of multiple batches. "
    "A shared entity is an investigation lead, not proof that it caused an outbreak."
)
common_entities = find_common_entities(chain)
if common_entities.empty:
    st.info("No entities are currently shared across multiple batch paths in the uploaded supply-chain data.")
else:
    st.dataframe(common_entities, use_container_width=True, hide_index=True)
    st.caption(
        "Check whether the shared entity supplied the relevant food during the exposure window. "
        "Incomplete or outdated supply-chain records can create false leads."
    )

st.subheader("Investigator notes")
st.markdown(
    "- Confirm report details, exposure windows, and supply-chain records before acting on a lead.\n"
    "- A shared supplier or a high score is not proof of contamination.\n"
    "- Synthetic demonstration data must not be represented as real illness surveillance.\n"
    "- The report-date filter is an 'as-of' view: reports received after the selected date are excluded, so the display does not use future reports.\n"
    "- Upstream/downstream paths and common entities depend on the links present in the CSV; missing links can hide connections."
)

st.download_button(
    "Download current ranking as CSV",
    data=ranking.to_csv(index=False).encode("utf-8"),
    file_name="batch_investigation_ranking.csv",
    mime="text/csv",
    disabled=ranking.empty,
)
