# Architecture

The pipeline has six stages, each with one job and a clear input and output, so
a reviewer can follow the data from raw source to analysis. Storage is local
parquet and jsonl; there is no database, because the scale does not need one and
a database would hurt reproducibility.

## Stage 1: ingest, config-driven

Each source is a YAML file under `configs/sources/`. A small engine reads it,
calls the named loader to fetch raw rows, and the named mapper to produce
canonical records. There are two extension points: loaders (how to fetch) and
transforms (how to map fields). A standard tabular source is expressed entirely
in configuration through the `generic_tabular` mapper and a `field_map`;
LocalView is a pure config. Sources with composite identifiers, such as
MeetingBank whose rows are agenda segments with an encoded uid, use a small
named mapper as a documented escape hatch. The point is that adding a typical
new source, or a new topic, is configuration rather than new code.

The canonical record (see `schema.py`) holds jurisdiction (name, FIPS, state),
meeting (date, type), transcript and a quality tier, and full provenance
(source, source_url, source_record_id). MeetingBank's native unit is a segment,
so its mapper groups segments into meetings; because we sample, a meeting is
often represented by some of its segments, so a full_text quality tier means
verbatim text is present, not that the whole meeting is captured. LocalView
spans governing-body types; we keep councils, county bodies, and planning or
zoning boards, mapped into the council-centric meeting_type, and a v2 schema
should add a dedicated government_type field.

## Stage 2: entity resolution

Two sources will describe some of the same meetings, and a single source can
capture one meeting in several records (LocalView posts a meeting as multiple
videos). Records that share the canonical key (jurisdiction_fips, meeting_date,
meeting_type) are the same meeting. We rank source quality (full_text > summary
> metadata_only), choose a primary, link the rest with full provenance, and
write any field disagreement to a ConflictRecord side table. Records are linked,
never silently collapsed, so every output row can be audited back to its
sources. Measured overlap is reported honestly: within LocalView this links
about forty meetings; cross-source overlap between MeetingBank and LocalView is
near zero by construction.

## Stage 3: extraction, two methods compared

A transparent lexicon classifier and an optional LLM both classify excerpts into
adaptation, mitigation, both, or unrelated, with a hazard tag and a confidence.
The lexicon is a tunable YAML a domain expert can read and edit, and it is the
scalable default. The methods are compared on a held-out hand-labeled golden set
in stage 6. The lexicon config is also the topic definition: swapping it
retargets the pipeline to a new topic with no code change.

## Stage 4: enrichment

Jurisdictions are rolled up to Census regions, and joined to FEMA National Risk
Index county hazard scores so the analysis can ask whether higher-exposure
places take more matching adaptation. County resolution uses a hardcoded map for
the MeetingBank cities, a name match for county-type jurisdictions, and an
optional place-to-county crosswalk for full place coverage. Unresolved
jurisdictions get null exposure and are reported as a coverage gap; we never
guess.

## Stage 5: analysis

Summaries answer the research question: action intensity by region and state,
adaptation by hazard type, action versus hazard exposure, and trends over time.
Everything that can be is normalized by meeting count, so results report
behavior rather than where we happen to have data. A coverage table makes the
representativeness limits explicit. Intensity remains confounded by transcript
depth across sources, which is stated alongside the numbers.

## Stage 6: evaluation

Precision, recall, and F1 by category against the golden set, plus confidence
calibration and human-vs-model Cohen's kappa. The harness runs a classifier
directly on the labeled excerpts, so the lexicon and the LLM are scored the same
way. Agreement between the annotator and a method is reported as exactly that,
not as inter-annotator agreement, which would require a second human annotator.

## Data flow

```
configs/sources/*.yaml
   -> [ingest engine]  -> data/interim/canonical.jsonl
   -> [dedup]          -> meetings.parquet + provenance + conflicts
   -> [extract]        -> actions.parquet  (lexicon | llm)
   -> [enrich + analyze] -> data/processed/analysis/*.parquet
   -> [eval vs golden] -> data/processed/eval_reports/*.json
   -> [app]            -> the Streamlit walkthrough
```

## Scale

The lexicon runs over the full corpus for free in seconds, so the first-pass
characterization scales to 10,000 meetings directly. Dedup blocks by (state,
year) to stay near-linear rather than quadratic. Runs are idempotent and
columnar. The LLM is reserved for ambiguous cases, which bounds its cost.
