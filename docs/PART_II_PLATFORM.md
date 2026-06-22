# Part II: from one-off workflow to a reusable capability

This is the five-minute talk for the panel. The frame: most of this pipeline is
already the reusable part, and the config-driven design makes that concrete
rather than aspirational. Turning it into a multi-lab capability is mostly
drawing a clean line between what each lab owns and what DISSC maintains, and
being honest about when it is worth doing.

## What is already reusable

Adding a source is a YAML file, and retargeting the topic is a different lexicon
YAML. The ingestion contract, the deduplication engine, the evaluation harness,
the canonical schema, and the deployment pattern do not change between topics.
That is the platform; it exists today as configuration plus a small engine.

## What each lab owns versus what DISSC owns

Each lab owns its topic lexicon (climate today, housing or wildfire next), its
source list, its taxonomy, and its golden set. DISSC owns the ingestion engine
and loaders, the dedup and entity-resolution layer, the eval harness, the schema,
and the infrastructure. The community can contribute new source loaders by
reviewed pull request.

## Onboarding

A template repo, three YAML files (sources, lexicon, taxonomy), and about two
hundred hand-labeled rows for the gold set. With a one-hour office hour, a new
lab is live in roughly two weeks. No lab writes ingestion or dedup code.

## Support and maintenance

Three tiers. The lab owns taxonomy, prompts, and gold set. The DISSC core team
owns the engine, loaders, eval harness, and infrastructure. The community
contributes loaders, reviewed by the core team. Each lab's output is a versioned,
DOI-tagged dataset, so results are citable and reproducible.

## The recommendation, stated plainly

A platform costs more than a pipeline, and it should not always be built. The
break-even is around three to four labs. My recommendation to DISSC would be to
ship Professor Rodriguez's project as a clean, documented pipeline first, and to
stand up the shared platform once a second lab needs the same thing. Building it
earlier is premature generalization; building it later means every lab reinvents
deduplication and evaluation. Knowing when not to build the platform is the
senior call, and it is the same discipline that keeps the first project shippable.
