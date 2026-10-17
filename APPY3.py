import os
search_folder = r"C:\Users\abhij\Downloads"

for root, dirs, files in os.walk(search_folder):
    for file in files:
        if file.lower() == "wards_30.csv":
            print("Found:", os.path.join(root, file))
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Mumbai Foodborne Signal Desk", page_icon="🩺", layout="wide")
ROOT=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(ROOT,"data")
REPORT_PATH=os.path.join(DATA,"synthetic_illness_reports.csv")

@st.cache_data(ttl=60)
def load_reports():
    df=pd.read_csv(REPORT_PATH)
    for c in ["symptom_onset_date","reporting_date"]: df[c]=pd.to_datetime(df[c],errors="coerce")
    return df

def daily_view(df, selected_day):
    """Daily simulated arrivals: today's snapshot varies by date but remains reproducible that day."""
    seed=int(selected_day.strftime("%Y%m%d")); rng=np.random.default_rng(seed)
    # Keep historic report rows; add a small date-seeded set of newly reported simulated cases.
    out=df.copy()
    n=int(rng.integers(2,10))
    wards=pd.read_csv(os.path.join(DATA,"wards_30.csv")); vendors=pd.read_csv(os.path.join(DATA,"vendors.csv")); foods=pd.read_csv(os.path.join(DATA,"food_items.csv"))
    onset_base=pd.Timestamp(selected_day)
    add=[]
    for j in range(n):
        ix=int(rng.integers(0,len(wards))); v=vendors.iloc[int(rng.integers(0,len(vendors)))]; f=foods.iloc[int(rng.integers(0,len(foods)))]
        delay=int(rng.choice([3,8,18,30,54,78],p=[.12,.2,.28,.2,.13,.07]))
        onset=onset_base-pd.Timedelta(days=int(rng.integers(0,8)))
        rep=onset+pd.Timedelta(hours=delay)
        sev=str(rng.choice(["Low","Moderate","High","Critical"],p=[.25,.46,.24,.05]))
        add.append({"report_id":f"LIVE-{selected_day:%Y%m%d}-{j+1:02d}","sheet_group":"Daily simulated feed","ward_id":wards.iloc[ix].ward_id,"ward_code":wards.iloc[ix].ward_code,"ward_name":wards.iloc[ix].ward_name,"vendor_id":v.vendor_id,"vendor_supplier_source":v.vendor_name,"illness_type":str(rng.choice(["Gastroenteritis","Acute diarrhoeal illness","Food poisoning suspected","Vomiting and diarrhoea"])),"severity":sev,"symptom_onset_date":onset,"reporting_date":rep,"reporting_delay_hours":delay,"food_type":f.food_name,"person_id":f"LIVE-P-{selected_day:%Y%m%d}-{j+1:02d}","batch_id":"","hospitalised":sev in ["High","Critical"] and bool(rng.integers(0,2)),"synthetic_data":True,"planted_signal_tags":"DAILY_SIMULATED"})
    out=pd.concat([out,pd.DataFrame(add)],ignore_index=True)
    out["reporting_date"]=pd.to_datetime(out.reporting_date,errors="coerce"); out["symptom_onset_date"]=pd.to_datetime(out.symptom_onset_date,errors="coerce")
    return out, n

def add_flags(df):
    x=df.copy(); x["red_flags"]=""
    delay=pd.to_numeric(x.reporting_delay_hours,errors="coerce")
    x.loc[delay>48,"red_flags"] += "Late report (>48h); "
    dup=x.person_id.astype(str).duplicated(keep=False)
    x.loc[dup,"red_flags"] += "Possible duplicate person ID; "
    # Isolated = no other report within same ward and 3-day onset window
    counts=[]
    for _,r in x.iterrows():
        nearby=((x.ward_id==r.ward_id)&((x.symptom_onset_date-r.symptom_onset_date).abs().dt.days<=3)).sum()-1
        counts.append(nearby)
    x["nearby_same_ward_3d"]=counts
    x.loc[x.nearby_same_ward_3d==0,"red_flags"] += "Isolated case; "
    # Popular food is a lead, not proof: flag only for investigation of potential misleading association.
    food_counts=x.groupby("food_type").report_id.transform("count")
    x.loc[(x.food_type.isin(["Vada Pav","Pav Bhaji","Samosa","Pani Puri","Biryani"])) & (food_counts>=4),"red_flags"] += "Popular-food signal (verify source); "
    # cluster heuristic: same vendor + onset window; counts do not establish causality
    for vendor, inds in x.groupby("vendor_supplier_source").groups.items():
        sub=x.loc[list(inds)]
        for idx,r in sub.iterrows():
            peers=sub[(sub.symptom_onset_date-r.symptom_onset_date).abs().dt.days<=3]
            if len(peers)>=4: x.loc[idx,"red_flags"] += "Vendor/onset cluster candidate; "
    x["red_flags"]=x.red_flags.str.strip().str.rstrip(";")
    x["flag_status"]=np.where(x.red_flags.eq(""),"No rule-based flag","Review")
    return x

st.title("🩺 Foodborne Illness Surveillance & Source Tracing")
st.caption("Mumbai / BMC ward-level investigation workspace · synthetic training data only · not a clinical diagnosis or live surveillance feed")
with st.sidebar:
    st.header("Investigation controls")
    selected_day=st.date_input("Simulation date",value=date.today())
    min_severity=st.multiselect("Severity",["Low","Moderate","High","Critical"],default=["Low","Moderate","High","Critical"])
    wards_all=pd.read_csv(os.path.join(DATA,"wards_30.csv"))
    ward_pick=st.multiselect("Ward",wards_all.ward_name.tolist())
    flags_only=st.checkbox("Show red-flagged reports only",value=False)
    st.caption("Daily synthetic arrivals are date-seeded: same date = same demo feed; next date = different arrivals.")
base=load_reports(); data,new_n=daily_view(base,selected_day); data=add_flags(data)
# Dynamic daily KPI reflects selected reporting date, with generated daily arrivals explicitly marked
live_count=int((data.reporting_date.dt.date==selected_day).sum())
if min_severity: data=data[data.severity.isin(min_severity)]
if ward_pick: data=data[data.ward_name.isin(ward_pick)]
if flags_only: data=data[data.flag_status=="Review"]

k1,k2,k3,k4,k5=st.columns(5)
k1.metric("Reports in view",f"{len(data):,}")
k2.metric("Selected-day reports",f"{live_count:,}",help="Includes the date-seeded simulated daily feed and any matching report dates.")
k3.metric("Flagged for review",f"{(data.flag_status=='Review').sum():,}")
k4.metric("High / critical",f"{data.severity.isin(['High','Critical']).sum():,}")
k5.metric("Wards represented",f"{data.ward_id.nunique():,}")
st.info(f"Demo feed generated {new_n} new simulated reports for {selected_day:%d %b %Y}. No real personal or patient data is used in the generated records.")

tab1,tab2,tab3,tab4,tab5=st.tabs(["Overview","Red flags & case search","Source tracing","Batch trace & common entities","Data export"])
with tab1:
    c1,c2=st.columns(2)
    with c1:
        trend=data.groupby(data.reporting_date.dt.date).size().reset_index(name="reports"); trend.columns=["reporting_date","reports"]
        st.plotly_chart(px.line(trend,x="reporting_date",y="reports",markers=True,title="Reports by reporting date"),use_container_width=True)
    with c2:
        sev=data.groupby("severity").size().reset_index(name="reports")
        st.plotly_chart(px.bar(sev,x="severity",y="reports",color="severity",title="Severity distribution"),use_container_width=True)
    c3,c4=st.columns(2)
    with c3:
        ward_counts=data.groupby("ward_name").size().reset_index(name="reports").sort_values("reports",ascending=False).head(15)
        st.plotly_chart(px.bar(ward_counts,x="reports",y="ward_name",orientation="h",title="Reports by ward (top 15)"),use_container_width=True)
    with c4:
        foods=data.groupby("food_type").size().reset_index(name="reports").sort_values("reports",ascending=False).head(12)
        st.plotly_chart(px.bar(foods,x="food_type",y="reports",title="Frequently reported food types"),use_container_width=True)

    st.subheader("Ranked probable leads")
    st.caption(
        "Sources are ranked for investigation triage using the reports currently in view. "
        "The score is a transparent heuristic, not a probability or a finding of causation."
    )
    lead_data=data.dropna(subset=["vendor_supplier_source"]).copy()
    if lead_data.empty:
        st.info("No vendor/source values are available in the current report view to rank.")
    else:
        lead_data["person_key"]=lead_data["person_id"].astype("string").str.strip()
        lead_data.loc[lead_data["person_key"].isin(["", "<NA>", "nan", "None"]), "person_key"]=pd.NA
        lead_data["report_key"]=lead_data["report_id"].astype("string").str.strip()
        leads=lead_data.groupby("vendor_supplier_source", dropna=True).agg(
            reports=("report_key", "nunique"),
            unique_people=("person_key", "nunique"),
            wards_affected=("ward_id", "nunique"),
            high_critical=("severity", lambda s: s.isin(["High", "Critical"]).sum()),
            first_onset=("symptom_onset_date", "min"),
            last_onset=("symptom_onset_date", "max"),
        ).reset_index()
        # Normalize each dimension against the strongest source in this current view.
        # Weights are intentionally visible and illustrative, not epidemiologically validated.
        score=pd.Series(0.0, index=leads.index)
        for column, weight in [("unique_people", 0.40), ("wards_affected", 0.25), ("high_critical", 0.25), ("reports", 0.10)]:
            maximum=leads[column].max()
            if pd.notna(maximum) and maximum > 0:
                score += leads[column] / maximum * weight
        leads["priority_score"]=(score*100).round(1)
        leads=leads.sort_values(["priority_score", "unique_people", "high_critical", "reports"], ascending=False).reset_index(drop=True)
        leads.insert(0, "rank", range(1, len(leads)+1))
        leads=leads.rename(columns={
            "vendor_supplier_source":"Probable lead / source",
            "reports":"Reports",
            "unique_people":"Unique person IDs",
            "wards_affected":"Wards affected",
            "high_critical":"High / critical reports",
            "first_onset":"First symptom onset",
            "last_onset":"Latest symptom onset",
            "priority_score":"Priority score / 100",
        })
        for col in ["First symptom onset", "Latest symptom onset"]:
            leads[col]=pd.to_datetime(leads[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("Unknown")
        st.dataframe(leads, use_container_width=True, hide_index=True)
        st.caption(
            "Scoring weights: unique people 40%, wards affected 25%, high/critical reports 25%, "
            "and distinct report IDs 10%, each normalized against the highest source value in the current view. "
            "Repeated person IDs do not inflate the unique-person component. Popular foods, delayed reports, "
            "isolated cases, and missing exposure details can mislead; review the red flags and verify exposure, "
            "batch, inspection, and laboratory evidence before drawing conclusions."
        )
    st.subheader("Ward coverage")
    coverage=wards_all.merge(data.groupby("ward_id").size().rename("reports"),on="ward_id",how="left").fillna({"reports":0})
    st.dataframe(coverage.rename(columns={"ward_name":"Ward","ward_code":"Ward code","zone":"Zone","reports":"Reports"})[["Ward","Ward code","Zone","Reports"]],use_container_width=True,hide_index=True)
with tab2:
    st.subheader("Search by person ID, vendor, report ID, food, or ward")
    q=st.text_input("Search records",placeholder="e.g. SYN-P-0001, Anand Snacks, Vada Pav")
    view=data.copy()
    if q:
        mask=view.astype(str).apply(lambda col: col.str.contains(q,case=False,na=False)).any(axis=1); view=view[mask]
    cols=["report_id","person_id","ward_name","vendor_supplier_source","illness_type","severity","symptom_onset_date","reporting_date","reporting_delay_hours","food_type","red_flags"]
    st.dataframe(view[cols].sort_values("reporting_date",ascending=False),use_container_width=True,hide_index=True)
    st.caption("Rules are triage heuristics. A popular food alone is not evidence of contamination; isolated cases are not automatically low-risk. Verify records and interview/exposure data.")
with tab3:
    st.subheader("Vendor / supplier source concentration")
    source=(data.groupby(["vendor_supplier_source","food_type"], dropna=False)
        .agg(reports=("report_id","nunique"),
             ward_count=("ward_id","nunique"),
             high_critical=("severity",lambda s:s.isin(["High","Critical"]).sum()),
             first_onset=("symptom_onset_date","min"),
             last_onset=("symptom_onset_date","max"))
        .reset_index())
    # Show ward names and codes together; preserve distinct wards and sort for easy scanning.
    ward_labels=(data.dropna(subset=["ward_id"])
        .assign(ward_label=lambda d: d["ward_name"].fillna("Unknown ward").astype(str)
                + " (" + d["ward_code"].fillna("No code").astype(str) + ")")
        .groupby(["vendor_supplier_source","food_type"], dropna=False)["ward_label"]
        .agg(lambda values: ", ".join(sorted(set(values))))
        .rename("wards"))
    source=source.merge(ward_labels.reset_index(), on=["vendor_supplier_source","food_type"], how="left")
    source=source.sort_values(["reports","high_critical","ward_count"],ascending=False).reset_index(drop=True)
    source.insert(0, "Rank", range(1, len(source)+1))
    source=source.rename(columns={"vendor_supplier_source":"Vendor / Supplier Source",
                                  "food_type":"Food Type", "reports":"Reports",
                                  "ward_count":"Number of wards", "wards":"Ward name (ward code)",
                                  "high_critical":"High / critical reports",
                                  "first_onset":"First symptom onset", "last_onset":"Latest symptom onset"})
    st.dataframe(source,use_container_width=True,hide_index=True)
    st.subheader("Potential source investigation")
    source_name=st.selectbox("Select source/vendor",sorted(data.vendor_supplier_source.dropna().unique()))
    sub=data[data.vendor_supplier_source==source_name]
    st.write(f"**{source_name}** — {len(sub)} reports across {sub.ward_name.nunique()} wards; {sub.severity.isin(['High','Critical']).sum()} high/critical reports.")
    st.dataframe(sub[["report_id","ward_name","person_id","food_type","batch_id","symptom_onset_date","reporting_date","severity","red_flags"]],use_container_width=True,hide_index=True)
    st.warning("Source ranking is a prioritization aid, not causal attribution. Confirm with exposure histories, batch records, inspection results, and lab evidence.")

with tab4:
    st.subheader("Recorded supply-chain batch tracing")
    st.caption("This view uses the supplied supply_chain_events.csv. Links show recorded movements, not proof that a batch caused illness.")
    chain_path=os.path.join(DATA,"supply_chain_events.csv")
    if os.path.exists(chain_path):
        chain=pd.read_csv(chain_path)
        needed={"batch_id","from_entity_id","from_entity_type","to_entity_id","to_entity_type","event_type"}
        if needed.issubset(chain.columns):
            available_batches=sorted(set(data.batch_id.dropna().astype(str)) & set(chain.batch_id.dropna().astype(str)))
            if not available_batches:
                available_batches=sorted(chain.batch_id.dropna().astype(str).unique())
                st.info("No batch IDs overlap between the current report view and supply-chain records. Showing recorded supply-chain batches for exploration.")
            if available_batches:
                selected_batch=st.selectbox("Select batch",available_batches,key="trace_batch")
                edges=chain[chain.batch_id.astype(str)==selected_batch].copy()
                st.dataframe(edges,use_container_width=True,hide_index=True)
                entities=sorted(set(edges.from_entity_id.dropna().astype(str)) | set(edges.to_entity_id.dropna().astype(str)))
                if entities:
                    entity=st.selectbox("Trace from entity",entities,key="trace_entity")
                    upstream_map={}
                    downstream_map={}
                    for row in edges.itertuples(index=False):
                        src=str(row.from_entity_id); dst=str(row.to_entity_id)
                        upstream_map.setdefault(dst,set()).add(src)
                        downstream_map.setdefault(src,set()).add(dst)
                    def walk_trace(start, adjacency):
                        seen=set(); stack=list(adjacency.get(start,set()))
                        while stack:
                            node=stack.pop()
                            if node==start or node in seen: continue
                            seen.add(node); stack.extend(adjacency.get(node,set())-seen)
                        return sorted(seen)
                    upstream=walk_trace(entity,upstream_map); downstream=walk_trace(entity,downstream_map)
                    a,b=st.columns(2)
                    with a:
                        st.markdown(f"**Upstream of {entity}**")
                        st.write(" → ".join(upstream) if upstream else "No recorded upstream links.")
                    with b:
                        st.markdown(f"**Downstream of {entity}**")
                        st.write(" → ".join(downstream) if downstream else "No recorded downstream links.")
            common_rows=[]
            for row in chain.dropna(subset=["batch_id","from_entity_id","to_entity_id"]).itertuples(index=False):
                common_rows.extend([{"entity":str(row.from_entity_id),"batch_id":str(row.batch_id)},
                                    {"entity":str(row.to_entity_id),"batch_id":str(row.batch_id)}])
            if common_rows:
                common=pd.DataFrame(common_rows).drop_duplicates().groupby("entity").agg(
                    batch_count=("batch_id","nunique"),
                    batch_ids=("batch_id",lambda x:", ".join(sorted(x.unique())))
                ).reset_index()
                common=common[common.batch_count>1].sort_values(["batch_count","entity"],ascending=[False,True])
                st.subheader("Entities shared across multiple batches")
                if common.empty: st.info("No entity is recorded across multiple batches.")
                else: st.dataframe(common,use_container_width=True,hide_index=True)
        else:
            st.error("Supply-chain CSV is missing required columns.")
    else:
        st.info("No supply_chain_events.csv found in the data folder.")

with tab5:
    st.subheader("Export filtered report view")
    st.download_button("Download CSV",data.to_csv(index=False).encode("utf-8"),file_name=f"surveillance_{selected_day.isoformat()}.csv",mime="text/csv")
    st.download_button("Download five-sheet synthetic workbook",open(os.path.join(ROOT,"synthetic_surveillance_reports.xlsx"),"rb").read(),file_name="synthetic_surveillance_reports.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.subheader("Data dictionary")
    st.markdown("- **person_id**: synthetic deduplication key; duplicates are deliberately planted for testing.\n- **vendor_supplier_source**: candidate exposure source, not proven source.\n- **reporting_delay_hours**: onset-to-report delay; >48 hours flagged.\n- **planted_signal_tags**: scenario annotations for QA; should not be treated as field evidence.\n- **synthetic_data**: true for all generated demo rows.")
