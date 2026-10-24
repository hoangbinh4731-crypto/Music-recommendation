# Handoff

Date: 2026-10-24

The full picture is `docs/GUIDE.md`: original idea, what is done, what is left, and how to run the demo. Read that first. This file is only the UI notes.

V1 of the recommender is done. The next person owns the web UI only. Do not change the Spark jobs, the feature definition, or the API contract unless the owner asks.

Read `docs/PLAN.md`, then `docs/updates/001-vector-dim.md`, `002-full-medium.md`, and `003-install-status.md`. This file is the state after those jobs were run. It does not replace the plan.

## What is done

- Offline jobs have been run on the full FMA medium set. No 12,000 cap. `VECTOR_DIM` is 36.
- `data/processed/` contains `subset_manifest.json`, `tracks.parquet`, `bad_tracks.csv`, `features_raw.parquet`, `features.parquet`, `scaler/`, `neighbors.parquet`, `mood_report.json`.
- Counts from the run: 25,000 mp3 files in, 24,985 playable tracks, 15 unreadable, 5,281 with Echo Nest labels. Every track has at least 5 neighbors. Extract wrote 24,985 rows and 0 null drops.
- Mood report: n=5281, arousal Pearson 0.41, valence Pearson 0.15. The report is not shown in the UI and does not feed the API.
- `pytest` from `music-recommendation/`: 17 passed. Tests use tiny fixtures. They do not need the FMA download.
- Browser check, while logged in: search, play, 20 similar tracks, For you omits the played track.

## How to run

From `music-recommendation/`:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH=src
export PYSPARK_PYTHON="$PWD/.venv/bin/python"
export PYSPARK_DRIVER_PYTHON="$PWD/.venv/bin/python"
export MUSICREC_JWT_SECRET=dev-secret
.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In another shell, from `music-recommendation/web/`:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173`, not `http://127.0.0.1:5173`.

Both servers were stopped on 2026-09-27. Start them again before checking the UI.

Spark jobs are already done. Do not re-run extract unless the features change. Extract on 25k tracks takes several minutes once, and much longer if the result is not cached. JDK 17 is required. The default `java` on this machine is not 17. Spark workers must use the venv Python 3.11. System Python is 3.9 and the job crashes with `PYTHON_VERSION_MISMATCH`.

## Product flow

Spark runs offline only. A request never starts Spark.

1. `jobs/run_subset.py` keeps medium tracks that have a non-empty title and a readable mp3. Output: `tracks.parquet`.
2. `jobs/run_extract.py` turns each file into 36 floats: MFCC mean 20, chroma mean 12, tempo, spectral centroid, RMS energy, zero-crossing rate. Spark `StandardScaler` (with mean, with std) writes `features.parquet`. The job repartitions to `defaultParallelism` and caches the extract so librosa does not run again for the scaler.
3. `jobs/run_neighbors.py` finds up to 20 nearest tracks with `BucketedRandomProjectionLSH`. If a track has fewer than 5 neighbors inside the distance threshold, exact distance fills that list up to 20. Output: `neighbors.parquet`.
4. `jobs/run_eval_mood.py` writes `mood_report.json` only.

The API loads the three Parquet tables into memory at startup.

- `GET /tracks/search?q=` is a case-insensitive substring match on title or artist, capped at 20. It does not use the vector. Empty `q` returns 20 tracks ordered by `track_id`.
- `GET /audio/{id}` returns the mp3. No login.
- `POST /play/{id}` requires the `access_token` cookie. It inserts one `listening_history` row and returns the precomputed neighbors with title and artist. It does not recompute distance.
- `GET /recommend/history` requires login. It builds a weighted mean of the played vectors (newest play has rank 0, weight `1 / (1 + rank)`), then returns the 20 nearest tracks not in that user's history. Empty history returns the 20 lowest `track_id`s.

Password hashing is bcrypt. The session is a JWT in an httpOnly cookie `access_token`, `samesite=lax`, `secure=false`, `max_age=604800`. CORS origin is `http://localhost:5173` with credentials. Do not set `allow_origins=["*"]`.

## UI rules that stay

Files: `web/src/`. Styles live in `web/src/index.css`.

Routes: `/`, `/login`, `/register`, `/track/:id`, `/for-you`.

`web/src/api.js` must keep `credentials: "include"` and `API_BASE = "http://localhost:8000"`. The page is on `localhost` and the cookie is host-scoped. `127.0.0.1` and `localhost` are different sites, so a cookie set by one is not sent to the other. That mismatch made `POST /play` return 401 while the audio player still worked.

`web/src/pages/Track.jsx` keeps an in-flight map around `POST /play`. React Strict Mode mounts the effect twice in dev. Without the map, one visit writes two history rows. A later visit of the same track should still write a new row after the first request finishes.

Do not add a mood label, a mood badge, a chart, a playlist editor, or cover art. Do not call Spotify. Do not read `features.csv` as model input.

## Known UI gaps

These are the reasons the current screen is not ready to hand to a listener. Behavior first, look second.

1. The nav always shows "Log in". It never shows the current user and there is no logout control. `POST /auth/logout` exists and clears the cookie.
2. Opening `/track/:id` while logged out calls `POST /play` and renders the raw body `{"detail":"Unauthorized"}`. Similar stays empty. The audio element still plays, because `GET /audio/{id}` does not require login. Neighbors for that track already exist. Track 737 has 20 of them. For a demo, log in first. Do not change the API so Similar works without a cookie.
3. Search, For you, and the track page show the raw response text on any error.
4. Search shows nothing until submit. There is no empty-state line.
5. Genre is returned by the API and not shown. Showing it is optional. Do not treat genre as the definition of a similar track.
6. The layout is one left-aligned column, max 40rem, serif, default browser audio control. That is the draft. The owner wants it replaced. The look is not chosen yet. Ask before inventing a new visual system.

Demo rule, decided 2026-10-24: log in before opening a track or For you. Similar and history stay behind the cookie. Do not add a logged-out path that still returns neighbors.

Still open, not approved:

- After login, show the username and a logout action. Register already navigates to `/login`. Keep that.
- Replace the raw JSON error with one sentence. This is polish. It is not a reason to remove the login requirement.

## What "similar" means

Similar is the 20 nearest tracks in the scaled 36-float space. It is not "same genre".

A check that compares the API list to the exact top 20 of the same vectors is circular. It will read about 100% when the job worked. It does not say the songs sound alike.

Genre overlap on the real catalog, measured 2026-09-26: mean 40.6% of neighbors share `genre`, versus 17.2% for two random tracks. Track 737 is Soul-RnB and 0 of its 20 neighbors share that genre. Genre is a weak outside label, not the pass rule.

Echo Nest is a company Spotify bought in 2014. `data/raw/fma_metadata/echonest.csv` stores their automatic audio scores for 5,281 catalog tracks: acousticness, danceability, energy, instrumentalness, liveness, speechiness, tempo, valence. Those scores are another machine description of the audio. They are not human similarity judgments. A held-out check that ignored energy and tempo (already in the 36-vector) found neighbors about 19% closer than a random Echo Nest track (median ratio 0.81, 3,340 tracks scored). That is a sanity check, not a decision to change the features.

For you cannot be scored from this demo. The only listeners are the owner and maybe one teammate on localhost. The field scores that endpoint by hiding part of a real listening history. This app does not have that history.

A human check that does fit a local demo: play three clips drawn at random, not from each other's neighbor lists, and ask which clip is the odd one out. Score the fraction of triplets where the 36-float distances pick the same odd clip. Chance is about 33%. A published Euclidean audio baseline on MagnaTagATune was about 68%. This test has not been run. It is not required for V1.

## Do not

- Re-download FMA. Audio is `data/raw/fma_medium/` (about 23GB). Metadata is `data/raw/fma_metadata/`. Zips stay next to those folders. macOS `unzip` cannot read `fma_medium.zip`. It was extracted with `tar -xf`.
- Commit `data/`, `.venv/`, or `web/node_modules/`.
- Commit unless the owner asks.
- Put mood text on a track page.
