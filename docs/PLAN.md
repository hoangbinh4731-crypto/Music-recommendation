# Music Recommendation on Spark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a content-based music recommender that extracts audio features from Free Music Archive (FMA) clips with Spark, precomputes neighbors, and serves search, playback, and listening-history recommendations from a local web app.

**Architecture:** One offline batch writes Parquet (features, track metadata, top-N neighbors). One online process (FastAPI) reads that Parquet and a SQLite file. React talks only to FastAPI. Spark does not run on user requests. `features.csv` is never the extraction input. Echo Nest labels are used only to score a mood heuristic, and mood is not shown in the UI. At about 10k tracks, Spark is there to show a design that scales past one machine. The defense should say that plainly.

**Tech Stack:** Python 3.11, Java 17, PySpark 3.5.4, librosa 0.10.2, Parquet via PyArrow, FastAPI, SQLite, React (Vite).

**Spec:** `de_an_music_recommendation_spark.pdf` at the repo root. This plan is the working copy of that brief. Later changes do not rewrite history inside this file. Add a new file under `music-recommendation/docs/updates/` and follow the update rule below.

## How updates work

This file stays the base plan. A change becomes a new doc:

`music-recommendation/docs/updates/NNN-short-title.md`

`NNN` is a three-digit sequence starting at `001`. Each update states the date, which section of this plan it overrides, the new decision, and why. Executors read this plan first, then every update in numeric order. The latest update wins on the sections it names. Do not delete superseded text here. Point to the update instead.

Current updates: `001-vector-dim.md` (vector length 36), `002-full-medium.md` (no 12,000 cap), `003-install-status.md` (medium, metadata, and JDK 17 are on disk; Spark jobs are not run), `004-current-state.md` (jobs have been run; read `docs/GUIDE.md`).

## Global Constraints

- All new files live under `music-recommendation/`. Do not edit Ceph deck files, `build_ceph_custom.js`, `build_ceph_deck.py`, or `package.json` at the repo root.
- V1 only. V2 mood playlists are out of scope until an update doc adds them.
- Do not display a mood label on a track.
- Do not call Spotify. Do not use `features.csv` as model input.
- Spark master is `local[*]`. No cluster manager.
- Audio root, metadata zip contents, Parquet, and `app.db` stay under `music-recommendation/data/` and are gitignored.
- Sample rate for extraction is 22050 Hz, mono.
- Neighbor list length is 20 (`TOP_N = 20`).
- Feature vector length is 35 floats, in this order: MFCC mean 20, chroma mean 12, tempo, spectral centroid mean, RMS energy, zero-crossing rate.
- Scaled vectors use Spark MLlib `StandardScaler` (with mean, with std). Save the scaler model under `data/processed/scaler`.
- Similarity is Euclidean top-N from `BucketedRandomProjectionLSH` (`bucketLength=2.0`, `numHashTables=4`, join threshold `2.0`). Self-matches are dropped.
- Password hashing is bcrypt. Session is a JWT in an httpOnly cookie named `access_token`, `samesite=lax`, `secure=false`, `max_age=604800`.
- CORS origin is `http://localhost:5173` with credentials enabled. Do not use `allow_origins=["*"]`.
- Code, comments, and commit messages are English.
- Commit a task only when the user asked to commit in that session.

## File map

```
music-recommendation/
  docs/PLAN.md
  docs/updates/
  requirements.txt
  .gitignore
  src/musicrec/config.py
  src/musicrec/subset.py
  src/musicrec/features.py
  src/musicrec/neighbors.py
  src/musicrec/mood.py
  jobs/run_subset.py
  jobs/run_extract.py
  jobs/run_neighbors.py
  jobs/run_eval_mood.py
  api/main.py
  api/db.py
  api/auth.py
  api/catalog.py
  web/                      # Vite app, Task 11
  tests/test_subset.py
  tests/test_features.py
  tests/test_neighbors.py
  tests/test_mood.py
  tests/test_auth.py
  tests/test_catalog.py
  tests/test_history.py
  data/                     # gitignored
    raw/fma_metadata/
    raw/fma_medium/
    processed/subset_manifest.json
    processed/bad_tracks.csv
    processed/features.parquet
    processed/tracks.parquet
    processed/neighbors.parquet
    processed/scaler/
    processed/mood_report.json
    app.db
```

Processed Parquet columns:

- `tracks.parquet`: `track_id` int, `title` string, `artist_name` string, `genre` string, `has_echonest` bool, `audio_path` string
- `features.parquet`: `track_id` int, `mfcc` array<double> length 20, `chroma` array<double> length 12, `tempo` double, `spectral_centroid` double, `energy` double, `zcr` double, `features` vector (MLlib, scaled, length 35)
- `neighbors.parquet`: `track_id` int, `neighbor_ids` array<int> length up to 20, `neighbor_distances` array<double> same length, ascending distance

SQLite:

- `users(id integer primary key, username text unique, password_hash text, created_at text)`
- `listening_history(id integer primary key, user_id integer, track_id integer, played_at text)`

---

### Task 1: Scaffold

**Files:**
- Create: `music-recommendation/requirements.txt`
- Create: `music-recommendation/.gitignore`
- Create: `music-recommendation/src/musicrec/config.py`
- Create: `music-recommendation/src/musicrec/__init__.py`
- Test: import check, no network

**Interfaces:**
- Consumes: nothing
- Produces: `musicrec.config` constants listed in Global Constraints, plus paths `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`, `DB_PATH`

- [ ] **Step 1: Write `requirements.txt`**

```
pyspark==3.5.4
librosa==0.10.2.post1
numpy==2.1.3
pandas==2.2.3
pyarrow==18.1.0
fastapi==0.115.6
uvicorn==0.34.0
sqlalchemy==2.0.36
pyjwt==2.10.1
bcrypt==4.2.1
python-multipart==0.0.20
httpx==0.28.1
pytest==8.3.4
soundfile==0.12.1
```

- [ ] **Step 2: Write `.gitignore`**

Ignore `data/`, `.venv/`, `__pycache__/`, `web/node_modules/`, `web/dist/`, `.pytest_cache/`.

- [ ] **Step 3: Write `config.py` with the constants in Global Constraints**

Paths are relative to `music-recommendation/`:

```python
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "app.db"
SR = 22050
N_MFCC = 20
N_CHROMA = 12
TOP_N = 20
LSH_BUCKET_LENGTH = 2.0
LSH_NUM_HASH_TABLES = 4
LSH_DISTANCE_THRESHOLD = 2.0
VECTOR_DIM = 35
```

- [ ] **Step 4: Create the virtualenv and install**

Run from `music-recommendation/`:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Expected: `pip` exits 0. `java -version` prints 17. If Java is missing, stop and tell the user. Do not install Java yourself.

- [ ] **Step 5: Import check**

```bash
.venv/bin/python -c "import musicrec.config as c; assert c.VECTOR_DIM == 35"
```

Expected: no output, exit 0. Run with `PYTHONPATH=src`.

---

### Task 2: Subset manifest from metadata

**Files:**
- Create: `music-recommendation/src/musicrec/subset.py`
- Create: `music-recommendation/jobs/run_subset.py`
- Test: `music-recommendation/tests/test_subset.py`

**Interfaces:**
- Consumes: FMA `tracks.csv` and `echonest.csv` already unzipped at `data/raw/fma_metadata/`
- Produces: `build_subset(tracks, echonest_ids, medium_ids) -> pandas.DataFrame` with columns `track_id, title, artist_name, genre, has_echonest`. `tracks` is a flat frame with those columns except `has_echonest`.
- Produces: `data/processed/subset_manifest.json` written by `jobs/run_subset.py`, fields `track_count`, `echonest_count`, `track_ids`

Metadata must already be on disk before this task runs. Download `fma_metadata.zip` from the mirror listed in the [FMA README](https://github.com/mdeff/fma) and unzip into `data/raw/fma_metadata/`. Do not download `fma_medium.zip` in this task.

Read the csv files the way the FMA loader does:

```python
tracks = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
echonest = pd.read_csv(echonest_csv, index_col=0, header=[0, 1, 2])
```

Columns:

- title: `("track", "title")`
- artist: `("artist", "name")`
- genre: `("track", "genre_top")`
- Echo Nest energy: `("echonest", "audio_features", "energy")`
- Echo Nest valence: `("echonest", "audio_features", "valence")`

`build_subset` takes flat columns, not the MultiIndex. The loader maps those tuples into `title`, `artist_name`, `genre` before calling it. Tests build that flat frame directly.

`medium_ids` is the set of track ids that exist as files under `data/raw/fma_medium/` once audio is present. Until audio exists, `jobs/run_subset.py` accepts `--medium-ids-csv` with one id per line. Tests pass a fake id list and do not read the real zip.

Selection rule inside `build_subset`:

1. Keep medium ids that also have a non-empty title.
2. Mark `has_echonest` when the id is in the Echo Nest index.
3. Sort so `has_echonest=True` rows come first, then by `track_id`.
4. Keep at most 12000 rows.
5. Do not drop non-Echo Nest rows if the intersection is under 10000. Record both counts. Do not invent a target the files cannot meet.

- [ ] **Step 1: Write the failing test**

```python
def test_build_subset_prefers_echonest_and_caps_at_12000():
    tracks = pd.DataFrame(
        {
            "track_id": [1, 2, 3, 4],
            "title": ["a", "b", "", "d"],
            "artist_name": ["aa", "bb", "cc", "dd"],
            "genre": ["Rock", "Pop", "Rock", "Jazz"],
        }
    )
    out = build_subset(tracks, echonest_ids={2, 4}, medium_ids={1, 2, 3, 4})
    assert list(out["track_id"]) == [2, 4, 1]
    assert list(out["has_echonest"]) == [True, True, False]
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_subset.py::test_build_subset_prefers_echonest_and_caps_at_12000 -v
```

Expected: FAIL, `build_subset` missing.

- [ ] **Step 3: Implement `build_subset` and `load_medium_ids(audio_root) -> set[int]`**

`load_medium_ids` reads `**/*.mp3`, stem is the zero-padded track id (`000002.mp3` -> `2`).

- [ ] **Step 4: Re-run the test**

Expected: PASS.

- [ ] **Step 5: Run the job once metadata is on disk**

```bash
PYTHONPATH=src .venv/bin/python jobs/run_subset.py --metadata data/raw/fma_metadata --medium-ids-csv data/raw/medium_ids.csv
```

Expected: `subset_manifest.json` exists and `track_count <= 12000`. Print `track_count` and `echonest_count`. If metadata is not downloaded yet, leave this step unchecked and stop this task at the unit test.

---

### Task 3: Drop unreadable audio

**Files:**
- Modify: `music-recommendation/src/musicrec/subset.py`
- Modify: `music-recommendation/jobs/run_subset.py`
- Test: `music-recommendation/tests/test_subset.py`

**Interfaces:**
- Consumes: manifest track ids and mp3 paths
- Produces: `probe_audio(path, sr=22050) -> bool` and `data/processed/bad_tracks.csv` columns `track_id,reason`
- Produces: `tracks.parquet` containing only probes that returned true

- [ ] **Step 1: Write the failing test using a tiny wav written with `soundfile`**

```python
def test_probe_audio_accepts_wav_and_rejects_missing(tmp_path):
    good = tmp_path / "000001.wav"
    sf.write(good, np.zeros(22050, dtype="float32"), 22050)
    assert probe_audio(good) is True
    assert probe_audio(tmp_path / "missing.wav") is False
```

`probe_audio` uses `librosa.load(path, sr=22050, mono=True, duration=5)`. Any exception returns False.

- [ ] **Step 2: Run the test, confirm FAIL, then implement**

- [ ] **Step 3: Wire the job**

For each manifest id, path is `data/raw/fma_medium/{id//1000:03d}/{id:06d}.mp3`. Probe. Write bad rows to csv. Write good rows to `tracks.parquet`.

This step stays unchecked until `fma_medium` audio is on disk. Unit test must pass without that download.

Expected full run: `bad_tracks.csv` row count printed. FMA documents a few hundred unreadable files. A count of 0 on a partial copy is acceptable. A crash on the first bad file is not.

---

### Task 4: Extract features

**Files:**
- Create: `music-recommendation/src/musicrec/features.py`
- Create: `music-recommendation/jobs/run_extract.py`
- Test: `music-recommendation/tests/test_features.py`

**Interfaces:**
- Consumes: `tracks.parquet` column `audio_path`
- Produces: `extract_track(path: str) -> dict` with keys `mfcc` (20), `chroma` (12), `tempo`, `spectral_centroid`, `energy`, `zcr`
- Produces: `raw_vector(row) -> list[float]` length 35, order fixed in Global Constraints
- Produces: `data/processed/features_raw.parquet` with those columns and `track_id` (unscaled). Scaling is Task 5.

```python
def extract_track(path: str, sr: int = 22050) -> dict:
    y, sr = librosa.load(path, sr=sr, mono=True)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20).mean(axis=1)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)
    tempo = float(librosa.feature.rhythm.tempo(y=y, sr=sr)[0])
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    energy = float(librosa.feature.rms(y=y).mean())
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())
    return {
        "mfcc": mfcc.astype("float64").tolist(),
        "chroma": chroma.astype("float64").tolist(),
        "tempo": tempo,
        "spectral_centroid": centroid,
        "energy": energy,
        "zcr": zcr,
    }
```

- [ ] **Step 1: Test `raw_vector` length and order**

Build a dict with known numbers. Assert `raw_vector` returns mfcc, then chroma, then the four scalars, length 35.

- [ ] **Step 2: Test `extract_track` on a 1-second sine wav**

Assert each array length and that every value is finite.

- [ ] **Step 3: Spark job**

`jobs/run_extract.py` starts `SparkSession.builder.master("local[*]").getOrCreate()`, loads `tracks.parquet`, and runs a `pandas_udf` that calls `extract_track` per path. The udf returns the raw columns. Write `features_raw.parquet`. One failed file logs the track id and yields nulls. Drop null rows after the udf and append those ids to `bad_tracks.csv`.

Group the udf as a pandas grouped map or a scalar iterator udf on the `audio_path` column. Do not `collect` paths to the driver and loop.

- [ ] **Step 4: Tests pass without a Spark cluster**

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_features.py -v
```

The Spark job itself is checked by running it on the sine-wav fixture copied into a one-row `tracks.parquet` under `tmp_path`. That test can be marked slow. Expected: one output row, `mfcc` length 20.

Full 10k run stays unchecked until audio is present. Expect roughly 30–60 minutes on a laptop. Print input rows, output rows, and null drops.

---

### Task 5: Scale vectors

**Files:**
- Modify: `music-recommendation/src/musicrec/features.py`
- Modify: `music-recommendation/jobs/run_extract.py`
- Test: `music-recommendation/tests/test_features.py`

**Interfaces:**
- Consumes: `features_raw.parquet`
- Produces: `data/processed/features.parquet` with MLlib vector column `features`
- Produces: scaler at `data/processed/scaler` via `StandardScalerModel.save`

- [ ] **Step 1: Test that a two-row matrix becomes mean 0 on a single column**

Assemble two raw vectors `[0,0,...,0]` and `[2,0,...,0]` is awkward at dim 35. Test the assembler with dim 35: row A all zeros, row B a 1 in index 0 only. After `StandardScaler` with mean and std, the two scaled values at index 0 are finite and their mean is about 0 (tolerance 1e-6). Other indexes may be 0 when std is 0. Define std 0 as scaled value 0. Spark's `StandardScaler` already does this when `withStd` is true and std is 0.

- [ ] **Step 2: Implement `assemble_and_scale(spark, raw_df)`**

Use `VectorAssembler` on a single double array if you explode to 35 columns, or build the vector in the udf with `Vectors.dense(raw_vector(row))` before scaling. Input column name to the scaler: `raw_features`. Output column name: `features`.

- [ ] **Step 3: Run pytest**

Expected: PASS. Full-data write of `features.parquet` is part of the same job as Task 4 once audio exists.

---

### Task 6: Neighbors

**Files:**
- Create: `music-recommendation/src/musicrec/neighbors.py`
- Create: `music-recommendation/jobs/run_neighbors.py`
- Test: `music-recommendation/tests/test_neighbors.py`

**Interfaces:**
- Consumes: `features.parquet` column `features`
- Produces: `top_n_from_pairs(pairs, top_n) -> DataFrame` columns `track_id, neighbor_ids, neighbor_distances`
- Produces: `data/processed/neighbors.parquet`
- Produces: `fill_short_lists(neighbors, features, top_n, min_count=5)` for tracks with fewer than 5 LSH neighbors. Fill uses exact Euclidean distance against the full vector set on the driver. 12000 x 35 floats fits in memory.

LSH settings come from `config.py`. Join:

```python
model = BucketedRandomProjectionLSH(
    inputCol="features",
    outputCol="hashes",
    bucketLength=LSH_BUCKET_LENGTH,
    numHashTables=LSH_NUM_HASH_TABLES,
).fit(features)
pairs = model.approxSimilarityJoin(
    features, features, LSH_DISTANCE_THRESHOLD, distCol="distance"
)
```

Drop rows where `datasetA.track_id == datasetB.track_id`. Keep the nearest `TOP_N` per `datasetA.track_id` with a window `row_number`.

- [ ] **Step 1: Test `top_n_from_pairs`**

Three tracks. Distances: (1,2)=0.1, (1,3)=0.4, (1,1)=0.0 already removed. `top_n=1` yields neighbor `[2]` and distance `[0.1]` for track 1.

- [ ] **Step 2: Test self is absent and distances are sorted ascending**

- [ ] **Step 3: Test `fill_short_lists`**

Track 1 has one neighbor. Two other unit vectors exist. After fill with `top_n=2` and `min_count=2`, track 1 has two neighbors and does not contain itself.

- [ ] **Step 4: Implement the Spark job and run pytest**

Full-data acceptance, checked only when `features.parquet` exists: every `track_id` in `tracks.parquet` appears in `neighbors.parquet`. Minimum neighbor count is at least 5. If not, set threshold to 4.0 in an update doc before changing `config.py`, then rerun this job once.

---

### Task 7: Mood heuristic report

**Files:**
- Create: `music-recommendation/src/musicrec/mood.py`
- Create: `music-recommendation/jobs/run_eval_mood.py`
- Test: `music-recommendation/tests/test_mood.py`

**Interfaces:**
- Consumes: raw (unscaled) `tempo`, `energy`, `spectral_centroid`, `zcr` for rows with `has_echonest`
- Produces: `scores(df) -> DataFrame` with `arousal`, `valence`
- Produces: `data/processed/mood_report.json` with `n`, `arousal_pearson`, `valence_pearson`

Formulas, applied after z-score inside the Echo Nest subset only:

```
arousal = 0.5 * z(tempo) + 0.5 * z(energy)
valence = 0.5 * z(spectral_centroid) - 0.5 * z(zcr)
```

`z` is `(x - mean) / std` on that subset. Std 0 yields 0.

Pearson is `pandas.Series.corr` against Echo Nest `energy` (for arousal) and `valence` (for valence). Write the two coefficients and `n`. Do not threshold them into a pass/fail. The report is the result.

- [ ] **Step 1: Test z-score formulas on a 4-row frame with hand-computed values**

- [ ] **Step 2: Test std 0 returns 0 and does not raise**

- [ ] **Step 3: pytest, then run the job when features and echonest metadata both exist**

This report does not feed the API or the UI.

---

### Task 8: Auth

**Files:**
- Create: `music-recommendation/api/db.py`
- Create: `music-recommendation/api/auth.py`
- Create: `music-recommendation/api/main.py`
- Test: `music-recommendation/tests/test_auth.py`

**Interfaces:**
- Produces: `create_user(username, password) -> User`
- Produces: `verify_password(password, password_hash) -> bool`
- Produces: `get_current_user(request) -> User` FastAPI dependency. Reads cookie `access_token`. Missing or bad token raises 401.
- Produces: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`

Register body: `{"username": str, "password": str}`. Duplicate username returns 409. Password shorter than 8 returns 422.

Login sets the cookie and returns `{"username": ...}` with no token in the JSON body. Logout deletes the cookie.

JWT payload: `sub` is the user id as a string, `exp` is 7 days from issue. Secret is read from env `MUSICREC_JWT_SECRET`. Tests set that env to `test-secret`. The app refuses to start if the env is missing.

- [ ] **Step 1: Test register and login with FastAPI `TestClient`**

Assert login response has `set-cookie` containing `access_token` and `HttpOnly`. Assert a follow-up `GET /auth/me` returns the username. Assert logout then `GET /auth/me` returns 401.

- [ ] **Step 2: Implement against a temp SQLite file via `MUSICREC_DB_PATH`**

- [ ] **Step 3: pytest `tests/test_auth.py`**

Expected: PASS.

---

### Task 9: Search, play, content neighbors

**Files:**
- Create: `music-recommendation/api/catalog.py`
- Modify: `music-recommendation/api/main.py`
- Test: `music-recommendation/tests/test_catalog.py`

**Interfaces:**
- Consumes: `tracks.parquet`, `neighbors.parquet`, cookie user
- Produces:
  - `GET /tracks/search?q=` returns up to 20 rows `{track_id, title, artist_name, genre}`. Match is casefold substring on title or artist. Empty `q` returns 20 rows ordered by `track_id`.
  - `GET /audio/{track_id}` returns the mp3 file. 404 if the id is not in `tracks.parquet`.
  - `POST /play/{track_id}` requires auth, inserts `listening_history`, returns `{track, neighbors}` where `neighbors` is the precomputed list with title and artist joined. Does not call Spark.

Load Parquet once at startup into memory with PyArrow. Tests build tiny Parquet fixtures in `tmp_path` and pass the directory through `MUSICREC_PROCESSED_DIR`.

- [ ] **Step 1: Test search hits artist case-insensitively and caps at 20**

- [ ] **Step 2: Test `POST /play/{id}` writes one history row and returns neighbor ids from the fixture, excluding the played id if it appears**

- [ ] **Step 3: pytest**

Expected: PASS.

---

### Task 10: History recommendation

**Files:**
- Modify: `music-recommendation/api/catalog.py`
- Test: `music-recommendation/tests/test_history.py`

**Interfaces:**
- Consumes: `listening_history` for the current user, scaled vectors from `features.parquet`, neighbor table is not required for this endpoint
- Produces: `GET /recommend/history` auth required
- Produces: `profile_vector(vectors, ranks) -> np.ndarray`

`ranks[i]` is 0 for the newest play. Weight is `1 / (1 + rank)`. Profile is the weighted mean of scaled vectors. Empty history returns 20 tracks ordered by `track_id` from the catalog (stable cold start, not random).

Nearest tracks: Euclidean distance from the profile to every scaled vector, drop track ids present in that user's history, return 20. Ties break by smaller `track_id`.

- [ ] **Step 1: Test weights**

Vectors `[0, 0]`, `[2, 0]` with ranks `[0, 1]`. Weights `1` and `0.5`. Mean is `[2/3, 0]`.

- [ ] **Step 2: Test the endpoint excludes played tracks**

- [ ] **Step 3: Test empty history returns the first 20 catalog ids**

- [ ] **Step 4: pytest**

Expected: PASS.

---

### Task 11: React client

**Files:**
- Create: `music-recommendation/web/` via `npm create vite@5 web -- --template react`
- Create: `web/src/api.js`
- Create: `web/src/pages/Login.jsx`
- Create: `web/src/pages/Register.jsx`
- Create: `web/src/pages/Search.jsx`
- Create: `web/src/pages/Track.jsx`
- Create: `web/src/pages/ForYou.jsx`
- Modify: `web/src/App.jsx`

**Interfaces:**
- Consumes: the API in Tasks 8–10
- Produces: routes `/login`, `/register`, `/`, `/track/:id`, `/for-you`
- `api.js` uses `fetch` with `credentials: "include"` and `API_BASE = "http://127.0.0.1:8000"`

Pages:

- Search: text input, submit, list results, link each row to `/track/:id`
- Track: `<audio controls src={API_BASE + "/audio/" + id}>`, then call `POST /play/{id}` and render neighbor links. No mood text.
- For you: `GET /recommend/history`, list links
- Login and register: forms posting to the auth endpoints

No chart library. No mood badge. No playlist editor.

- [ ] **Step 1: Scaffold Vite and add `react-router-dom`**

- [ ] **Step 2: Implement the five pages and `api.js`**

- [ ] **Step 3: Manual check**

Start API with `MUSICREC_JWT_SECRET` set and `uvicorn api.main:app --app-dir music-recommendation` from a path that imports `api`. Start Vite on port 5173. Register, search a known title from `tracks.parquet`, play, confirm a history row exists, open For you and confirm the played track is absent.

This manual check is the acceptance test for Task 11. It stays unchecked until processed Parquet exists.

---

## Out of scope

- Mood playlist page
- Genre picker at registration
- Postgres
- Spark on the request path
- Training a mood classifier
- Cover art

## Done when

1. `pytest` from `music-recommendation/` passes without the FMA download.
2. With metadata and medium audio present, the four jobs write manifest, tracks, features, neighbors, and `mood_report.json`.
3. A logged-in browser session can search, play a 30-second clip, see 20 content neighbors, and see history-based neighbors that omit played tracks.
