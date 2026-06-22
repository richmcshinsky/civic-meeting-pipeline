# Municipal Climate Action Pipeline

A reproducible pipeline and analysis that characterizes what US municipalities
are doing about climate change, from council-meeting transcripts, and how it
varies by region, hazard exposure, and time. Built as a response to a research
computing request from Professor Rodriguez at the Yale School of the
Environment.

The deliverable is an analysis a domain expert can act on, sitting on top of a
production-shaped, source-agnostic capability, presented through a Streamlit
walkthrough. The pipeline is the means; the analysis, the engineering
decisions, and the communication are the product.

Live walkthrough: run `make app` (or the deployed Streamlit link in the repo).

## What it answers

- How climate-action intensity varies by region and over time.
- Which hazards (flood, heat, wildfire, drought) adaptation targets.
- Whether higher-exposure places take more matching adaptation, by joining
  jurisdictions to the FEMA National Risk Index.
- All of it reported as "among covered jurisdictions", with the coverage and
  representativeness limits made explicit rather than hidden.

## How it runs

On a fresh clone:

```
make setup     # environment and dependencies (uv)
make all       # ingest, dedup, extract, analyze, eval
make app       # launch the Streamlit walkthrough
make test      # critical tests
```

The deployed app reads precomputed results, so it is fast, free to host, and
makes no model calls at runtime.

## Pipeline

1. **Ingest (config-driven).** Each source is a YAML file under
   `configs/sources/`. A standard tabular source needs only a config; the
   engine handles loading, field mapping, and sampling. LocalView is pure
   config; MeetingBank uses one small named mapper for its composite IDs.
2. **Entity resolution.** Records are linked on a canonical key (jurisdiction
   FIPS, meeting date, meeting type). The best-quality version is primary, the
   rest are kept with full provenance, and field disagreements go to a conflict
   side table. Nothing is silently collapsed.
3. **Extraction (two methods).** A transparent lexicon classifier
   (`configs/lexicon.climate.yaml`) and an optional LLM, compared on a
   hand-labeled golden set.
4. **Enrichment.** Region rollups and FEMA NRI hazard-exposure scores joined by
   county.
5. **Analysis.** Region, hazard type, hazard exposure, and time summaries,
   normalized by meeting count so results reflect behavior, not just coverage.
6. **Evaluation.** Precision, recall, F1 by category against the golden set,
   plus confidence calibration and human-vs-model agreement.

## Methods: why a lexicon, not just an LLM

"I ran an LLM" is not a method. We compared a tunable lexicon against a
zero-shot LLM on 130 hand-labeled excerpts. The lexicon wins decisively
(about 95 percent accuracy and 0.82 Cohen's kappa, versus roughly 81 percent
and 0.48 for the LLM), is interpretable enough for a domain expert to tune,
runs free over 10,000 meetings in seconds, and is exactly reproducible. The
LLM's only edge is the rare "both" category. So the recommendation is lexicon
as the scalable default, LLM to refine the ambiguous cases where the
evaluation shows it adds value.

## Adding a source is configuration, not code

A new tabular source is a YAML file. For example, the LocalView field mapping:

```yaml
field_map:
  jurisdiction_fips: {copy: st_fips}
  jurisdiction_name: {copy: place_name}
  state: {state_abbrev: state_name}
  meeting_date: {parse_date: {column: meeting_date, format: iso}}
  meeting_type: {meeting_type_from_govt: place_govt}
  transcript: {clean_text: {column: caption_text_clean, missing: "<no caption available>"}}
```

The same seam retargets the whole pipeline to a new topic: swap
`configs/lexicon.climate.yaml` for a housing or wildfire lexicon, no code
change. This is the foundation of the Part II platform story.

## Scaling to 10,000 meetings

The lexicon scales trivially (no per-call cost). Dedup blocks by (state, year)
to stay near-linear. Storage is columnar parquet; runs are idempotent. The LLM
is reserved for ambiguous cases, bounding its cost. Nothing here needs a
database at this scale.

## Honest limitations

- Coverage is not a random sample of US municipalities. MeetingBank is six
  large cities; LocalView omits the largest cities. Regional comparisons are
  "among covered jurisdictions".
- Action intensity is confounded by transcript depth: MeetingBank's full
  transcripts yield more candidate sentences than LocalView's short captions.
- The hazard-exposure correlation is computed over the counties we could
  resolve (small n), so it is directional, not a powered statistical claim.
- Cross-source overlap between MeetingBank and LocalView is near zero by
  construction; Council Data Project, the natural overlap partner, has been
  decommissioned.

## Repository layout

```
configs/sources/      one YAML per source (config-driven ingestion)
configs/lexicon.*.yaml the topic definition (tunable)
src/yse_meetings/      ingest, dedup, extract, enrich, analysis, eval
app/streamlit_app.py   the walkthrough
data/                  crosswalks and golden set committed; rest regenerated
docs/                  architecture, questions, Part II platform
tests/                 critical tests
```

## Data sources

- MeetingBank: https://meetingbank.github.io/
- LocalView: https://www.localview.net/ (doi:10.7910/DVN/NJTBEM)
- FEMA National Risk Index: https://hazards.fema.gov/nri/
- Council Data Project: https://councildataproject.org/ (backends decommissioned)
