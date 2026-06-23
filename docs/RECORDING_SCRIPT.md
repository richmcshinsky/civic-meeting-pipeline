# Recording script: Part I walkthrough (target 9 minutes)

Screen-share the Streamlit app and narrate. Times are guides. Speak to the
panel (faculty plus the data engineering and DISSC leads): calm, practical, no
hype. Part II is the live 5-minute talk at the interview, not in this recording.

## 0:00 - 1:00  Frame the problem (Overview section)

"Professor Rodriguez wants to characterize what US municipalities are doing on
climate adaptation and mitigation across about ten thousand council meetings,
and how that varies by region, hazard exposure, and time, from sources that
overlap and disagree."

Point at the three hard parts: finding the signal in noisy text, reconciling
overlapping sources without losing provenance, and being honest that this
corpus is not a random sample of US municipalities. Then read the top two or
three questions you would confirm with the lab first (discussion versus adopted
action; which regional taxonomy; the validation bar if it is publication grade).

## 1:00 - 3:00  Approach and data (Part I, tab 1)

Walk the architecture diagram left to right: sources in, one canonical record,
entity resolution, extraction, enrichment, analysis, with the golden set
evaluating extraction.

Two points to land: first, adding a source is a YAML config, not new code, which
is what makes Part II real. Second, deduplication links overlapping records and
keeps provenance rather than collapsing them, with conflicts sent to a review
table. Then the sources: MeetingBank and LocalView used, and why the other three
were not (CDP decommissioned, Hamlet's terms forbid redistribution, data.gov is
a registry). There's a full coverage breakdown by region and source in the app
for you to explore after.

## 3:00 - 5:30  Methods and evaluation (Part I, tab 2)

"I did not just run an LLM. I compared two methods on a hand-labeled set of 130
excerpts." Kappa measures agreement above chance, where 1.0 is perfect and 0.0
is chance, so the contrast between 0.82 and 0.48 is large. Show the two accuracy
numbers: lexicon about 95 percent, kappa 0.82; zero-shot LLM about 81 percent,
kappa 0.48. This is human-vs-model agreement, not full inter-annotator
agreement; a publication-ready validation would require a second annotator and a
measured IAA score.

Then the F1-by-category chart: the LLM only wins on the rare 'both' class, which
is exactly where the lexicon is weakest, so the recommendation is evidence
based: lexicon as the scalable, auditable default; the LLM to refine the
ambiguous cases. Note the lexicon is a tunable YAML a domain expert can edit,
and that confidence is validated against the golden set, not trusted blindly.

## 5:30 - 8:00  Findings (Part I, tab 3)

This is the answer to the actual question. The US map: where climate-action
intensity concentrates, white states are coverage gaps. Region bars: the West
leads, and immediately give the caveat that this is partly a source effect
(MeetingBank's full transcripts yield more candidate text than LocalView's short
captions). Hazard type: flood, heat, wildfire lead. Hazard exposure: joined to
the FEMA National Risk Index, higher-risk counties take more matching
adaptation, a positive correlation, with the honest caveat that n is small so it
is directional. Time: the trend line.

## 8:00 - 9:00  Reproducibility and close

"The whole thing reproduces with make setup and make all on a fresh clone, and
ships a versioned dataset other researchers can reuse." Add: "This isn't a
notebook, it's a proper pip-installable package with a CLI and tests, so another
lab can adopt it without reading the pipeline code." State the limitations
plainly: coverage skew, intensity confounded by transcript depth, small-n
exposure. Close: "The same config-driven design that makes this reproducible is
also what makes it a platform, which is what I'll walk through at the interview."

## Tips

- Keep the lexicon-versus-LLM contrast and the coverage caveats front and
  center; that calibration is what a data engineering lead and a stats-literate
  faculty panel reward.
- If you run long, compress the data-landscape detail; protect the findings and
  the methods comparison.
- Practice once to land under 10 minutes with margin.
