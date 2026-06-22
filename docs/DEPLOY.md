# Deploying the walkthrough to Streamlit Community Cloud

The app reads a committed snapshot in `data/demo`, so it runs on Streamlit
Cloud without the pipeline, Ollama, or large downloads.

## One time, before deploying

1. Build and commit the demo snapshot (after `make all`, `make eval`, and
   `make eval-llm` so the methods comparison is populated):

   ```
   uv run python scripts/build_demo_snapshot.py
   git add data/demo requirements.txt
   git commit -m "Add demo snapshot for Streamlit Cloud"
   ```

2. Confirm these are in the repo root or as expected:
   - `requirements.txt` (streamlit, pandas, pyarrow, plotly)
   - `app/streamlit_app.py`
   - `data/demo/` with `meetings.parquet`, `actions.parquet`,
     `analysis/*.parquet`, and `eval_reports/latest_lexicon.json` (plus
     `latest_llm.json` for the comparison).

3. Push to GitHub (public):

   ```
   git push origin main
   ```

## Deploy

1. Go to https://share.streamlit.io and sign in with GitHub.
2. New app -> pick `richmcshinsky/yale-yse-meeting-pipeline`, branch `main`,
   main file path `app/streamlit_app.py`.
3. Deploy. Streamlit installs from `requirements.txt` and serves the app.
4. Copy the public URL into the README (replace the placeholder) and use it in
   the submission email.

## Notes

- On Cloud there is no `data/processed`, so the app falls back to `data/demo`
  automatically. No code change needed.
- The app makes no model calls at runtime, so there is no API key to configure.
- If you update the analysis, rerun `scripts/build_demo_snapshot.py`, commit,
  and Cloud redeploys on push.
