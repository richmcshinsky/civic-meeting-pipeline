# Questions for Professor Rodriguez

Before writing code, these are the questions I would ask. They are ordered
roughly by how much each one would change the build. The first three are the
ones I would cover in the walkthrough, because the answers reshape the schema
and the validation bar, not just the parameters.

## The three I would lead with

1. What is the smallest version of this output that would change a decision a
   municipality makes? This forces a working definition of useful. If the
   answer is "a defensible count of who is doing what", the bar is different
   than if the answer is "a dataset another lab will cite".

2. Are you trying to characterize what councils talked about, or what they
   passed? These are different problems with different signals in a
   transcript. Discussion is abundant and noisy; adopted action is sparse and
   higher value. The extraction prompt and the eval both depend on this.

3. Will this be cited in a published paper? Published datasets carry a
   different validation bar than internal exploration. If yes, we invest more
   in inter-annotator agreement and a frozen, versioned release. If no, we
   can ship partial coverage with confidence scores and move faster.

## The rest

4. What time period matters most: the last five, ten, or twenty-five years?
   Retention varies enormously across sources, and this decides how much of
   the coverage gap is a real limitation versus an in-scope choice.

5. What is your tolerance for missing or low-confidence records? Do you want
   full coverage reported with confidence scores attached, or only
   high-confidence rows shipped? This sets the confidence threshold and how
   the coverage page is framed.

6. What regional taxonomy do you want: FEMA regions, EPA regions, climate
   zones, census divisions, or something custom? This shapes the schema and
   how "variation by region" is computed. You are the geospatial expert here,
   so I would defer to your preference.

7. For the extraction step, what is your appetite for human-in-the-loop
   validation on a sample? Even a few hundred reviewed labels changes the
   eval methodology and the credibility of the numbers.

8. What is the reuse path you actually want: raw extractions plus
   reproducible code, a curated and paper-ready dataset, or both? This
   decides where the effort goes between pipeline and packaging.
