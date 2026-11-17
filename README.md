# Tile-card generator — prototype

Pipeline (recommended): name → LLM (SYSTEM_PROMPT_1) → silhouette SVG → `solver.py` → 5×5 tile keys → `tilecard.js` → card.

* `catalog.json / catalog.js` — your 95 tiles vectorised (potrace) + every unique rotation/flip ("3a","3b"…). Rebuild with `build_catalog.py`.
* `solver.py <silhouette.svg>` — prints the 5×5 grid (restricted to the "clean" tile subset `CLEAN` inside the file).
* `tilecard.js` — deterministic renderer (Arabic + English name, number badge, outline icon). Works in browser or any JS runtime.
* `tile_card_tool.html` — paste JSON, see card, download SVG.
* `shoot.py` — headless PNG export (Playwright).
* `designs/` — the examples used in the tests. `examples/results.png` — rendered results.

Not included / not tested: the actual LLM call (needs your API key) and the vision-critique loop (done by hand in these tests).

## Web app (app/)
`app/server.py` (Flask) + `app/static/index.html` — user-facing page: generate images by name (no card), tick any number and add them to the library, optional card (color + name), library of past cards (search + reuse),
card color, name language (Arabic / English / both) and editable names, edit the drawing with a text comment, PNG / SVG / zip-of-all-attempts download.
* Run locally: `pip install flask cairosvg google-genai` then `GEMINI_API_KEY=... python app/server.py` → http://localhost:8000
* Try without a key: `MOCK=1 python app/server.py` (fake model, only to test the UI)
* In Colab: use `tile_cards_app.ipynb`.
* Library is stored as JSON files in `library/entries/` (override with `LIB_DIR`).

## Deploy for other people
`pip install -r requirements.txt` then `GEMINI_API_KEY=... gunicorn --chdir app --workers 1 --threads 16 --timeout 120 -b 0.0.0.0:8000 wsgi:app`
(or build the `Dockerfile`; mount a persistent volume at `/data`). Keep ONE gunicorn worker: the job queue is in memory.
Env: GEMINI_API_KEY, LIB_DIR, RATE_LIMIT (per IP per hour), WORKERS (parallel designs per card).
