.PHONY: setup test ingest dedup extract eval app clean all

# One-time setup on a fresh clone. Creates the venv and installs deps,
# including the dev tools used by the test suite.
setup:
	uv sync --extra dev

# Run the critical tests (dedup, extraction, schema).
test:
	uv run --extra dev python -m pytest tests/ -q

# Pull source samples and normalize into the canonical schema.
ingest:
	uv run python -m yse_meetings.cli ingest

# Link records, choose primaries by quality, write the conflict side table.
dedup:
	uv run python -m yse_meetings.cli dedup

# Extract actions. Default is the interpretable, scalable lexicon classifier.
extract:
	uv run python -m yse_meetings.cli extract --method lexicon

# Optional LLM extraction (needs Ollama running) for method comparison.
extract-llm:
	uv run python -m yse_meetings.cli extract --method llm

# Hand-label extracted actions into the golden set.
label:
	uv run python -m yse_meetings.label --n 80

# Build region / hazard / time analysis summaries.
analyze:
	uv run python -m yse_meetings.cli analyze

# Score the lexicon method against the golden set and write eval reports.
eval:
	uv run python -m yse_meetings.cli eval --method lexicon

# Score the LLM method (needs Ollama) for the method comparison.
eval-llm:
	uv run python -m yse_meetings.cli eval --method llm

# Launch the Streamlit demo locally.
app:
	uv run streamlit run app/streamlit_app.py

# Remove generated data, keep committed crosswalk and golden set.
clean:
	rm -rf data/raw data/interim data/processed

# End to end on a fresh clone: make setup && make all
all: ingest dedup extract analyze eval
	@echo "Pipeline complete. Run 'make app' to launch the demo."
