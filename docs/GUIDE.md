# Guide

Date: 2026-10-27

The GitHub front page is `README.md`. This file is the longer manual: what the system does, what is already finished, and what is left.

`docs/PLAN.md` is the original task list. Its checkboxes were never ticked. Do not treat an empty checkbox as unfinished work. `docs/updates/003-install-status.md` says the Spark jobs had not been run. That was true on 2026-09-26 and is no longer true. This guide wins on the current state.

The feature vector was extended from 36 to 75 floats on 2026-10-27 (`docs/updates/005-vector-75.md`). Code and this guide describe the 75-float version. Numbers measured on the 2026-09-26 run are 36-float numbers and are labelled as such.

## Original idea

Build a local music app on the Free Music Archive medium set.

The recommendation is content-based. Each clip becomes a vector of numbers taken from the audio itself. Tracks close to each other in that space are treated as similar. A second view, For you, mixes the vectors of tracks the logged-in user has already played and finds nearby tracks they have not played.

Spark does the heavy work once, offline, and writes tables. The website never starts Spark. A click only reads those tables. The point of Spark here is a design that can grow past one machine, even though this copy runs as `local[*]` on a laptop. Say that plainly if this is defended.

V1 is search, playback, 20 precomputed neighbors, and a history-based list. Mood playlists, a genre picker at signup, cover art, charts, and a playlist editor are out of scope. Do not show a mood label on a track. Do not call Spotify. Do not use `data/raw/fma_metadata/features.csv` as model input. That file is in the download for comparison only.

The working brief is `docs/PLAN.md`. Later decisions are `docs/updates/001-vector-dim.md` (the vector was 36 floats, not 35), `002-full-medium.md` (keep all of FMA medium, no 12,000 cap), `003-install-status.md` (where the files and JDK 17 are), `004-current-state.md` (the jobs were run), and `005-vector-75.md` (the vector is now 75 floats).

## What was built

One offline batch. One API. One small React app.

Offline, in order:

1. Choose tracks. Keep an FMA medium mp3 when the metadata title is non-empty and the file can be opened. Write `tracks.parquet`. Unreadable files go to `bad_tracks.csv`.
2. Describe each file as 75 floats, in this order: 20 MFCC means, 20 MFCC standard deviations, 12 chroma means, 12 chroma standard deviations, tempo, then five scalar features, each as a mean followed by a standard deviation: spectral centroid, spectral rolloff, spectral bandwidth, RMS energy, zero-crossing rate. `musicrec.features.feature_names()` lists the 75 names in order. Sample rate is 22050 Hz, mono. Only a 30 s window from the middle of the track is read. Silent audio, or a vector containing NaN or Inf, is rejected and the track goes to `bad_tracks.csv`. Scale each column to mean 0 and standard deviation 1 with Spark `StandardScaler`, so a large number like tempo does not drown the rest. Write `features_raw.parquet` (columns `track_id`, `raw`), `features.parquet` (adds `features` and `vector`, the scaled values) and `data/processed/scaler`.
3. For each track, store up to 20 nearest other tracks by Euclidean distance. The search uses Spark `BucketedRandomProjectionLSH` (`bucketLength=3.0`, `numHashTables=5`, join threshold `3.0`). The top 20 per track are chosen inside Spark with a window function. Self-matches and duplicate pairs are dropped. If a track gets fewer than 5 neighbors inside that threshold, exact distance fills the list up to 20. Write `neighbors.parquet`. The job prints how many tracks needed the exact fill (`fallback_tracks`).
4. Score a mood heuristic against Echo Nest energy and valence. The four raw inputs (tempo, energy, spectral centroid, zcr) are taken back out of the `raw` column with `musicrec.features.scalar_columns`. Write `mood_report.json`. Nothing in the API or the UI reads it.

Online:

- FastAPI loads `tracks.parquet`, `features.parquet` (only the `track_id` and `vector` columns), and `neighbors.parquet` into memory at startup. Accounts and play history live in SQLite `data/app.db`.
- React talks only to FastAPI.

Search does not use the vector. It is a case-insensitive substring match on title or artist, at most 20 rows.

Play does not measure distance again. It writes one history row and returns the neighbor list already stored for that track.

For you does use the vectors. The newest play has rank 0 and weight `1 / (1 + rank)`. The profile is the weighted mean of those scaled vectors. The endpoint returns the 20 nearest catalog tracks that are not already in that user's history. With no history it returns the 20 lowest track ids.

Auth: bcrypt passwords, minimum 8 characters. Session is a JWT in an httpOnly cookie named `access_token` (`samesite=lax`, `secure=false`, 7 days). The app refuses to start without `MUSICREC_JWT_SECRET`. CORS allows only `http://localhost:5173` with credentials.

Stack: Python 3.11, Java 17, PySpark 3.5.4 (3.1 or newer is required for `array_to_vector`), librosa, Parquet, FastAPI, SQLite, React (Vite).

## What is done

Measured on the real medium set, 2026-09-26, with the **36-float** vector. These are the baseline. The 75-float run is not measured yet; fill the right-hand column after the rerun.

| Result | 36 floats (2026-09-26) | 75 floats |
|---|---|---|
| mp3 files on disk | 25,000 | 25,000 |
| playable tracks | 24,985 | |
| unreadable audio | 15 | |
| tracks with Echo Nest labels | 5,281 | |
| feature rows written | 24,985, 0 null drops | |
| minimum neighbors per track | 5 | |
| tracks needing the exact fill | not recorded | |
| mood report n | 5,281 | |
| arousal Pearson vs Echo Nest energy | 0.41 | |
| valence Pearson vs Echo Nest valence | 0.15 | |

The mood inputs (tempo, energy, centroid, zcr) did not change, but the window is now 30 s from the middle of the track instead of the whole clip, so the Pearson values can move a little.

`pytest` from the repo root passed 17 tests on the 36-float code. After the 75-float change `tests/test_features.py` has 6 tests instead of 2, so the expected total is 21 (22 with the duplicate-pair test in `tests/test_neighbors.py`). Those tests use tiny fixtures and do not need the FMA files.

A logged-in browser session has searched, played a clip, seen 20 neighbors, and seen a For you list that omitted the played track. This was done on the 36-float tables and should be repeated once after the rerun.

Two fixes were required after the first run:

- Spark on this machine must use JDK 17 at `/opt/homebrew/opt/openjdk@17`. The default `java` is not 17, and Spark 3.5 fails on it. Workers must use `.venv/bin/python` (3.11). The system Python is 3.9 and the extract job dies with `PYTHON_VERSION_MISMATCH`.
- The browser must call `http://localhost:8000`, and the page must be opened at `http://localhost:5173`. `localhost` and `127.0.0.1` do not share cookies. The first UI build called `127.0.0.1`, so play returned 401 while the audio file still loaded.

`web/src/pages/Track.jsx` also dedupes the in-flight `POST /play`. React Strict Mode runs the effect twice in development. Without that guard, one visit wrote two history rows.

## What is left

The recommender behavior for V1 is done. What is left on the product side is the screen, and it belongs to the next person.

The current UI is a draft: one left-aligned column, max width 40rem, a serif font, and the browser's default audio control. Styles are in `web/src/index.css`.

Decided on 2026-10-24: for a demo, log in before opening a track or For you. Similar and history stay behind the cookie. Do not add a logged-out path that still returns neighbors. If someone opens a track while logged out, Similar is empty and the page shows `{"detail":"Unauthorized"}`. The mp3 still plays, because `GET /audio/{id}` does not require login. That screen is expected. It is not a missing neighbor table. Track 737 has 20 neighbors in `neighbors.parquet`.

Still open. Ask the owner before doing these:

- The nav always says "Log in". It does not show who is logged in, and there is no logout button. `POST /auth/logout` already clears the cookie.
- Errors print the raw response body. A sentence would be enough. That polish must not remove the login requirement.
- The visual layout is not chosen. Do not invent a new look. Ask first.
- Genre is in the API payload and is not shown. Showing it is optional. Do not define "similar" as "same genre".

Do not add a mood label, a chart, a playlist editor, or cover art. Do not change the 75-float definition again or re-run the Spark jobs unless the owner asks, except for the one rerun that update 005 requires. Extract on 25,000 files is the expensive step.

Open for the analysis side (not required for the demo):

- Rerun `run_extract.py`, `run_neighbors.py` and `run_eval_mood.py` once on the 75-float code, and fill the right-hand column of the table above. Keep the 36-float outputs in `data/processed_36/` before rerunning.
- Compare 36 and 75 floats with the genre overlap measure below (an evaluation job that reads `tracks.parquet` and `neighbors.parquet`).
- Tune `LSH_BUCKET_LENGTH`, `LSH_NUM_HASH_TABLES` and `LSH_DISTANCE_THRESHOLD` in `src/musicrec/config.py` against the `fallback_tracks` rate and the run time. The current values are a first guess for 75 dimensions.
- Time `run_neighbors.py` with `local[1]`, `local[2]`, `local[4]` and `local[*]` (pass the master as the first argument) for the scaling discussion.
- Check LSH recall against exact search on a sample of tracks.

Not required for this demo:

- Scoring For you from listening logs. This copy has one or two local users. The usual metric hides part of a large real listening history and checks whether those tracks come back. That history does not exist here.
- A human odd-one-out test on three random clips. That is the check that would say whether the feature distance matches a listener. It has not been run. Chance on that test is about one in three. A published Euclidean audio baseline on MagnaTagATune was about 68%.

"Similar" means nearest in the scaled 75-float space. Comparing the API list to the exact top 20 of those same vectors only checks that the job ran. It does not check that the songs sound alike. Genre overlap is a weak outside label. On the 36-float run, 40.6% of neighbors shared a genre, versus 17.2% for two random tracks. Track 737 is Soul-RnB and none of its 20 neighbors shared that genre. These are the baseline to beat or match after the rerun.

Echo Nest was a music-analysis company. Spotify bought it in 2014. FMA stores their automatic scores in `echonest.csv` for 5,281 of these tracks: acousticness, danceability, energy, instrumentalness, liveness, speechiness, tempo, valence. Those are machine scores, not human judgments. On the 36-float run, a check that held out the six scores the vector does not already include found neighbors about 19% closer than a random labeled track (median ratio 0.81, 3,340 tracks). That says the distance is not random. Repeat it on the 75-float vector for a like-for-like comparison.

## Install on a new machine

Git clone does not include `data/`, `.venv/`, or `web/node_modules/`. A new machine has code only. Search returns nothing and play has no audio until the steps below are done.

You need Python 3.11, Node.js with npm, and JDK 17. On this Mac, JDK 17 is Homebrew `openjdk@17` and is not the default `java`. Spark 3.5 fails on newer Java. Another machine can use its own JDK 17 path. The exports below assume Apple Silicon Homebrew. On Windows use PowerShell: `$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17..."`, `$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"`, `$env:PYTHONPATH = "src"`, and point `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` at `.venv\Scripts\python.exe`.

From the repo root (this folder, the one that contains `src/` and `web/`):

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```bash
cd web
npm install
cd ..
```

Download the two FMA archives from `https://os.unil.cloud.switch.ch/fma/`:

- `fma_metadata.zip` (about 0.3GB) into `data/raw/`
- `fma_medium.zip` (about 23GB) into `data/raw/`

The mirror drops connections. Resume a partial file with HTTP range requests. macOS `unzip` cannot read `fma_medium.zip`. Extract both with `tar -xf` so the result is:

- `data/raw/fma_metadata/tracks.csv` and `echonest.csv`
- `data/raw/fma_medium/000/*.mp3` through `155/`

`features.csv` will be inside the metadata folder. Leave it there. Do not use it as model input.

JDK 17 and the venv Python, every shell that runs Spark:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH=src
export PYSPARK_PYTHON="$PWD/.venv/bin/python"
export PYSPARK_DRIVER_PYTHON="$PWD/.venv/bin/python"
```

`$PWD` must be the repo root when you set the two PySpark variables. System Python 3.9 makes the extract job crash with `PYTHON_VERSION_MISMATCH`.

Then build the tables. This is required on a new machine. `data/processed/` is not in git. Subset walks every mp3. Extract is the long step.

```bash
.venv/bin/python -c "
from pathlib import Path
from musicrec.subset import load_medium_ids
ids = sorted(load_medium_ids('data/raw/fma_medium'))
Path('data/raw/medium_ids.csv').write_text('\n'.join(map(str, ids)) + '\n')
"
.venv/bin/python jobs/run_subset.py \
  --metadata data/raw/fma_metadata \
  --medium-ids-csv data/raw/medium_ids.csv \
  --audio-root data/raw/fma_medium
.venv/bin/python jobs/run_extract.py
.venv/bin/python jobs/run_neighbors.py
.venv/bin/python jobs/run_eval_mood.py
```

Subset prints progress every 1,000 tracks. Extract prints a batch count and, at the end, `dim`, seconds per track and core count; `dim` must be 75. Neighbors prints the minimum neighbor count, the number of tracks that needed the exact fill, the Spark master and the elapsed time. Mood prints one summary line at the end. Expect on the order of 25,000 playable tracks and a minimum of 5 neighbors.

Run `run_neighbors.py` again after every `run_extract.py`. It stops with an assertion if `features.parquet` does not have `VECTOR_DIM` columns. To run it on a different number of cores, pass the master: `.venv/bin/python jobs/run_neighbors.py "local[4]"`.

If the owner gives you a copy of `data/processed/` (about 37MB for the 36-float tables, larger for 75 floats), you can skip the four jobs. You still need the mp3 files. Playback reads the path stored in `tracks.parquet`. Check that the copy matches the code: its vectors must have 75 values.

## How to use the demo

Start the API from the repo root:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH=src
export MUSICREC_JWT_SECRET=dev-secret
.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Start the site from `web/`:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://localhost:5173`. Do not use `http://127.0.0.1:5173`.

Then:

1. Register a user. The password must be at least 8 characters. The app sends you to Log in.
2. Log in. Do this before any track or For you.
3. Search a word that appears in a title or an artist name, for example `love`. Submit. At most 20 rows come back. Click one.
4. The track page plays the clip and lists Similar. Similar is the stored neighbor list, not a new search.
5. Open For you. The track just played should be absent. With no plays, For you is the 20 lowest track ids.

The first API start loads about 25,000 rows into memory. Wait until the log says the application has started. Register a new account on a new machine. `data/app.db` is local and is not in git.

## How to run the tests

From the repo root:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Numba, which librosa uses, cannot write its cache inside a sandbox. Run this on a normal shell. Expected: 21 passed (22 with the duplicate-pair test).

## Files worth knowing

```
README.md                    GitHub front page
docs/PLAN.md                 original task list, checkboxes are stale
docs/updates/001-vector-dim.md
docs/updates/002-full-medium.md
docs/updates/003-install-status.md
docs/updates/004-current-state.md
docs/updates/005-vector-75.md
docs/GUIDE.md                this file
src/musicrec/                subset, features, neighbors, mood, config
jobs/                        the four offline commands
api/                         FastAPI, auth, catalog
web/src/                     the draft UI
data/raw/fma_medium/         25,000 mp3 files, about 23GB, gitignored
data/raw/fma_metadata/       tracks.csv, echonest.csv, features.csv
data/processed/              the tables the API reads
data/processed_36/           copy of the 36-float tables, for comparison (create it before rerunning)
data/app.db                  users and listening history
```

Audio path for track id `N` is `data/raw/fma_medium/{N//1000:03d}/{N:06d}.mp3`.

Do not commit `data/`, `.venv/`, or `web/node_modules/`. Do not commit unless the owner asks.

Run the four jobs again only when the feature definition or the neighbor settings change, or when `data/processed/` is missing. Use the commands in "Install on a new machine".
