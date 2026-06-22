# Action extraction prompt (v0.1)

This file is the version-controlled prompt for the extraction stage. Changes
here are tracked in git so the methods write-up can point to exactly which
prompt produced a given eval report.

## Task

You read an excerpt from a US municipal council meeting transcript. You
identify whether the council is discussing a concrete action related to
climate change, and you classify it.

## Definitions

- adaptation: action that prepares for or reduces harm from climate impacts
  already happening or expected (sea walls, cooling centers, floodplain
  zoning, wildfire defensible space).
- mitigation: action that reduces greenhouse gas emissions (building
  electrification, transit, renewable procurement, fleet conversion).
- both: a single action that clearly serves adaptation and mitigation.
- unrelated: not a climate action.

Hazard, when an adaptation action targets a specific threat: flood,
wildfire, heat, drought, storm, sea_level_rise, other, or none.

## Output

Return a single JSON object with one key, "actions", whose value is a list of
the climate actions found in the excerpt. Return nothing else.

```json
{
  "actions": [
    {
      "action_text": "verbatim excerpt, quoted from the transcript",
      "action_category": "adaptation | mitigation | both | unrelated",
      "hazard_type": "flood | wildfire | heat | drought | storm | sea_level_rise | other | none",
      "confidence": 0.0
    }
  ]
}
```

## Rules

- action_text must be a verbatim span from the input, not a paraphrase.
- Return one list item per distinct action. If the excerpt contains no climate
  action, return an empty list: {"actions": []}.
- hazard_type applies mainly to adaptation actions; use "none" when no single
  hazard applies.
- confidence is your calibrated probability that the classification is
  correct, from 0 to 1.
