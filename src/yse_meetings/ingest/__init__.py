"""Config-driven ingestion.

Sources are declared in configs/sources/*.yaml and run through the engine.
See engine.run_source and engine.available_sources. Loaders (how to fetch) and
transforms (how to map fields) are the two extension points; a standard
tabular source needs only a YAML config.
"""

from yse_meetings.ingest.engine import available_sources, run_source

__all__ = ["run_source", "available_sources"]
