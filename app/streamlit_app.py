"""Narrative Streamlit app for the YSE Research Computing exercise.

Structured to mirror the exercise: a Problem Overview, then Part I (approach,
methods, findings in tabs), then Part II (a reusable capability for multiple
labs). Built to be presented to the panel and to stand in for slides. Reads
precomputed tables from data/processed (or a committed data/demo snapshot);
no model calls at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/richmcshinsky/yale-yse-meeting-pipeline"

st.set_page_config(page_title="Municipal Climate Action | YSE", layout="wide")


def data_dir() -> Path:
    processed = REPO_ROOT / "data" / "processed"
    return processed if (processed / "meetings.parquet").exists() else REPO_ROOT / "data" / "demo"


@st.cache_data
def load() -> dict:
    d = data_dir()
    adir = d / "analysis"
    rd = lambda p: pd.read_parquet(p) if p.exists() else pd.DataFrame()
    rj = lambda p: json.loads(p.read_text()) if p.exists() else {}
    return {
        "dir": d,
        "meetings": rd(d / "meetings.parquet"),
        "actions": rd(d / "actions.parquet"),
        "provenance": rd(d / "provenance.parquet"),
        "by_region": rd(adir / "by_region.parquet"),
        "by_state": rd(adir / "by_state.parquet"),
        "by_time": rd(adir / "by_time.parquet"),
        "by_hazard": rd(adir / "by_hazard.parquet"),
        "exposure_j": rd(adir / "exposure_jurisdictions.parquet"),
        "exposure_a": rd(adir / "exposure_alignment.parquet"),
        "coverage": rd(adir / "coverage.parquet"),
        "eval_lex": rj(d / "eval_reports" / "latest_lexicon.json"),
        "eval_llm": rj(d / "eval_reports" / "latest_llm.json"),
    }


def scroll_to_top() -> None:
    """Reset scroll on section change and on tab clicks. Streamlit keeps scroll
    position otherwise, which is jarring in a presentation. The tab-click hook
    is installed once on the parent document."""
    components.html(
        """
        <script>
        const d = window.parent.document;
        const toTop = () => {
          d.querySelectorAll('section, [data-testid="stMain"], [data-testid="stAppViewContainer"]')
           .forEach(el => { try { el.scrollTo({top: 0, left: 0}); } catch (e) {} });
          try { window.parent.scrollTo(0, 0); } catch (e) {}
        };
        setTimeout(toTop, 40);
        if (!window.parent.__yseTabHook) {
          window.parent.__yseTabHook = true;
          d.addEventListener('click', (ev) => {
            if (ev.target.closest('button[data-baseweb="tab"]')) setTimeout(toTop, 40);
          }, true);
        }
        </script>
        """,
        height=0,
    )


ARCH_DOT = """
digraph G {
  rankdir=LR; bgcolor="transparent";
  node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 color="#cccccc"];
  edge [color="#9aa0a6" arrowsize=0.7];
  subgraph cluster_s {
    label="Sources (added by config)"; style=dashed; color="#bbbbbb"; fontname="Helvetica"; fontsize=10;
    MB [label="MeetingBank\\ndeep transcripts" fillcolor="#dbeafe"];
    LV [label="LocalView\\nbroad coverage" fillcolor="#dbeafe"];
  }
  ING [label="Ingest + normalize\\nYAML per source" fillcolor="#e0e7ff"];
  ER  [label="Entity resolution\\nlink + keep provenance" fillcolor="#e0e7ff"];
  EX  [label="Extraction\\nlexicon  |  LLM" fillcolor="#dcfce7"];
  EN  [label="Enrichment\\nregion + FEMA NRI" fillcolor="#dcfce7"];
  AN  [label="Analysis\\nregion · hazard · exposure · time" fillcolor="#fef9c3"];
  GOLD[label="Golden set" shape=note fillcolor="#fee2e2"];
  MB -> ING; LV -> ING; ING -> ER -> EX -> EN -> AN;
  GOLD -> EX [style=dashed label="evaluate" fontsize=9 fontname="Helvetica"];
}
"""

PLATFORM_DOT = """
digraph P {
  rankdir=LR; bgcolor="transparent";
  node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 color="#cccccc"];
  edge [color="#9aa0a6" arrowsize=0.7];
  L1 [label="Climate lab\\nlexicon + sources YAML" fillcolor="#dcfce7"];
  L2 [label="Housing lab\\nits YAML + gold set" fillcolor="#dcfce7"];
  L3 [label="Wildfire lab\\nits YAML + gold set" fillcolor="#dcfce7"];
  CORE [label="Shared core (DISSC)\\ningestion contract · dedup · eval · schema" fillcolor="#e0e7ff"];
  OUT [label="Versioned, DOI-tagged\\ndataset per lab" shape=note fillcolor="#fef9c3"];
  L1 -> CORE; L2 -> CORE; L3 -> CORE; CORE -> OUT;
}
"""


# ==========================================================================
def overview(data: dict) -> None:
    st.title("Characterizing municipal climate action")
    st.caption("YSE Research Computing exercise. A walkthrough of the approach, "
               "the analysis, and how it would scale to other labs.")

    st.markdown(
        "> *Analyze ~10,000 council meetings to characterize what municipalities "
        "are doing on climate adaptation and mitigation, and how it varies by "
        "region, hazard exposure, and time. The data are spread across multiple "
        "sources and formats, records may overlap, and the dataset and methods "
        "should be shareable.*  - Prof. Rodriguez"
    )

    m = data["meetings"]
    if not m.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Meetings (demo run)", len(m))
        c2.metric("Jurisdictions", m["jurisdiction_fips"].nunique())
        c3.metric("States", m["state"].nunique())
        c4.metric("Sources", m["source"].nunique())

    st.subheader("The three things that make this hard")
    a, b, c = st.columns(3)
    a.markdown("**1. Finding the signal**\n\nClimate actions are a small, noisy "
               "fraction of meeting text. Detection quality decides everything "
               "downstream.")
    b.markdown("**2. Reconciling sources**\n\nFormats differ and records overlap. "
               "We must link them without losing where each came from.")
    c.markdown("**3. Honest coverage**\n\nThis corpus is not a random sample of US "
               "municipalities, so regional claims need explicit caveats.")

    st.subheader("Questions I would confirm with the lab first")
    st.markdown(
        "- Discussion versus adopted action: which one are we counting?\n"
        "- Which regional taxonomy: Census, FEMA, or climate zones?\n"
        "- Which time window matters most, given source retention?\n"
        "- Publication-grade dataset, or internal exploration? Sets the bar.\n"
        "- Is there appetite for human review on a sample to anchor accuracy?"
    )


# ==========================================================================
def part1(data: dict) -> None:
    st.title("Part I: approach, methods, and findings")
    tab_a, tab_m, tab_f = st.tabs(["Approach and data", "Methods and evaluation", "Findings"])

    with tab_a:
        st.subheader("One pipeline, one canonical record")
        st.graphviz_chart(ARCH_DOT, use_container_width=True)
        st.markdown(
            "Every source is normalized into a single record shape, so adding a "
            "source is a configuration file rather than new code. Overlapping "
            "records are linked on a canonical key (jurisdiction, date, meeting "
            "type); the best-quality version becomes primary, the rest are kept "
            "with full provenance, and disagreements go to a review side table. "
            "Nothing is silently collapsed."
        )
        st.subheader("Sources reviewed")
        srcs = pd.DataFrame([
            {"source": "MeetingBank", "role": "Used: deep full-text transcripts, 6 cities", "status": "Backbone for accuracy"},
            {"source": "LocalView", "role": "Used: broadest US database, mid-size places", "status": "Backbone for breadth"},
            {"source": "Council Data Project", "role": "Natural overlap partner", "status": "Backend decommissioned"},
            {"source": "Hamlet", "role": "Commercial product", "status": "Terms forbid redistribution"},
            {"source": "data.gov", "role": "Catalog of meeting datasets", "status": "Registry layer, not transcripts"},
        ])
        st.dataframe(srcs, hide_index=True, use_container_width=True)
        cov = data["coverage"]
        if not cov.empty:
            st.subheader("Where the data actually is")
            pivot = cov.pivot_table(index="region", columns="source",
                                    values="meetings", aggfunc="sum", fill_value=0)
            st.bar_chart(pivot)
            st.caption("Coverage is uneven by design: MeetingBank is a few large "
                       "western cities, LocalView skews to mid-size places and "
                       "omits the largest cities. We report findings as 'among "
                       "covered jurisdictions'.")

    with tab_m:
        st.subheader("Two methods, measured against a hand-labeled set")
        st.markdown(
            "Rather than trust one model, I compared a transparent lexicon "
            "classifier against a zero-shot LLM on 130 hand-labeled excerpts. "
            "The lexicon is a tunable list of climate terms a domain expert can "
            "read and edit."
        )
        lex, llm = data["eval_lex"], data["eval_llm"]
        cols = st.columns(2)
        if lex.get("accuracy") is not None:
            cols[0].metric("Lexicon accuracy", f"{lex['accuracy']:.0%}",
                           f"kappa {lex.get('human_vs_model_cohen_kappa')}")
        if llm.get("accuracy") is not None:
            cols[1].metric("Zero-shot LLM accuracy", f"{llm['accuracy']:.0%}",
                           f"kappa {llm.get('human_vs_model_cohen_kappa')}")
        else:
            cols[1].metric("Zero-shot LLM accuracy", "run make eval-llm")

        if lex.get("per_category") and llm.get("per_category"):
            lf = {k: v["f1"] for k, v in lex["per_category"].items()}
            mf = {k: v["f1"] for k, v in llm["per_category"].items()}
            st.caption("F1 by category: lexicon vs LLM (higher is better, max 1.0)")
            st.bar_chart(pd.DataFrame({"lexicon": lf, "LLM": mf}), stack=False)
            st.caption("The LLM beats the lexicon only on the rare 'both' "
                       "category, which is exactly where the lexicon is weakest. "
                       "That is the concrete case for combining them.")
        elif lex.get("per_category"):
            st.caption("Lexicon F1 by category")
            st.bar_chart(pd.DataFrame(lex["per_category"]).T["f1"])

        st.subheader("The tradeoff, and the call")
        t1, t2 = st.columns(2)
        t1.markdown("**Lexicon**\n\nInterpretable, free, runs over 10k meetings in "
                    "seconds, exactly reproducible, and more accurate here. Weaker "
                    "on genuinely ambiguous phrasing.")
        t2.markdown("**LLM**\n\nBetter on the rare ambiguous 'both' cases, but "
                    "slower, costlier, opaque, and less well calibrated.")
        st.success("Recommendation: use the lexicon as the scalable, auditable "
                   "default, and route only the ambiguous cases to the LLM, the "
                   "one place the evaluation shows it adds value. Every prediction "
                   "is validated against the golden set rather than trusted blindly.")

    with tab_f:
        st.subheader("How climate action varies")
        st.caption("Intensity = climate actions per meeting, so results reflect "
                   "behavior, not just where we have data. Read as 'among covered "
                   "jurisdictions'.")
        bs, reg = data["by_state"], data["by_region"]
        if not bs.empty:
            st.markdown("**Where action concentrates** (intensity by state)")
            try:
                import plotly.express as px
                fig = px.choropleth(
                    bs, locations="state", locationmode="USA-states",
                    color="actions_per_meeting", scope="usa",
                    color_continuous_scale="Blues",
                    hover_data=["meetings", "climate_actions"],
                    labels={"actions_per_meeting": "actions / meeting"},
                )
                fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0), height=380,
                    paper_bgcolor="rgba(0,0,0,0)",
                    geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
                    font_color="#cccccc",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Shaded states are where we have coverage; white states "
                           "are gaps. Color is climate-action intensity per meeting.")
            except Exception:
                if not reg.empty:
                    st.bar_chart(reg.set_index("region")["actions_per_meeting"])
        if not reg.empty:
            st.markdown("**By region**")
            st.bar_chart(reg.set_index("region")["actions_per_meeting"])
            st.caption("The West leads, though this is partly a source effect: "
                       "MeetingBank's full transcripts there yield more candidate "
                       "text than LocalView's short captions elsewhere.")
        h, e = st.columns(2)
        haz = data["by_hazard"]
        if not haz.empty:
            h.markdown("**By hazard type** (adaptation)")
            h.bar_chart(haz.set_index("hazard_type")["actions"])
        ea = data["exposure_a"]
        if not ea.empty:
            e.markdown("**By hazard exposure** (FEMA NRI)")
            chart = ea.dropna(subset=["pearson_r_risk_vs_action"]).set_index("hazard")
            if not chart.empty:
                e.bar_chart(chart["pearson_r_risk_vs_action"])
            e.caption("Positive correlation: higher-risk counties take more "
                      "matching adaptation. Small n, so directional not definitive.")
        tm = data["by_time"]
        if not tm.empty:
            st.markdown("**Over time**")
            st.line_chart(tm.set_index("year")["actions_per_meeting"])


# ==========================================================================
def part2(data: dict) -> None:
    st.title("Part II: a reusable capability for multiple labs")
    st.markdown(
        "When other groups want the same workflow for housing or wildfire, most "
        "of this pipeline is already the reusable part. The work is drawing a "
        "clean line between what each lab owns and what DISSC maintains."
    )
    st.graphviz_chart(PLATFORM_DOT, use_container_width=True)
    a, b, c = st.columns(3)
    a.markdown("**Standardize (DISSC owns)**\n\nThe ingestion contract, the "
               "deduplication engine, the evaluation harness, the canonical "
               "schema, and the deployment pattern.")
    b.markdown("**Configure (each lab owns)**\n\nThe topic lexicon (climate today, "
               "housing next, just a different YAML), the source list, and the "
               "taxonomy. No engine changes.")
    c.markdown("**Onboard**\n\nA template repo, three YAML files, and a ~200-row "
               "gold set. A new lab is live in about two weeks.")
    st.subheader("Support model")
    st.markdown(
        "Three tiers: the lab owns its taxonomy, prompts, and gold set; the DISSC "
        "core team owns the engine, loaders, eval harness, and infrastructure; "
        "the community contributes new source loaders by reviewed pull request."
    )
    st.success(
        "The recommendation I would make to the panel: a platform costs more than "
        "a pipeline, and the break-even is around three to four labs. Ship "
        "Professor Rodriguez's project as a clean, documented pipeline first, and "
        "stand up the shared platform once a second lab needs the same thing. "
        "Building it earlier is premature generalization; building it later means "
        "every lab reinvents deduplication and evaluation."
    )
    st.caption(f"Code and documentation: {REPO_URL}")


SECTIONS = {
    "Problem overview": overview,
    "Part I: analysis and methods": part1,
    "Part II: reusable platform": part2,
}


def main() -> None:
    data = load()
    st.sidebar.title("Walkthrough")
    choice = st.sidebar.radio("Section", list(SECTIONS), label_visibility="collapsed")
    st.sidebar.caption("Reads precomputed results; no model calls at runtime.")
    scroll_to_top()
    SECTIONS[choice](data)


if __name__ == "__main__":
    main()
