# Music recommendation

A local content-based recommender for the [Free Music Archive](https://github.com/mdeff/fma) medium set. Spark turns each clip into a 75-number audio vector and stores the 20 nearest tracks. The website only reads those tables. A click does not start Spark.

Search matches a title or an artist name. Similar is the stored neighbor list. For you mixes the vectors of tracks you have played and skips those tracks.

This repository is the code and the docs. It does not contain the audio, the Parquet tables, or user accounts. A fresh clone cannot play a clip until you download FMA and build `data/processed/`.

## Requirements

- Python 3.11
- Node.js and npm
- JDK 17

Spark 3.5 fails on newer Java. On this Mac, JDK 17 is Homebrew `openjdk@17`, and it is not the `java` on the default `PATH`. Point `JAVA_HOME` at whatever JDK 17 you installed.

## Install

From the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```bash
cd web && npm install && cd ..
```

Download `fma_metadata.zip` and `fma_medium.zip` from `https://os.unil.cloud.switch.ch/fma/` into `data/raw/`. Extract both with `tar -xf`. macOS `unzip` cannot read the medium archive. You should end up with `data/raw/fma_metadata/tracks.csv` and `data/raw/fma_medium/000/*.mp3`.

`features.csv` is in the metadata download for comparison only. Do not use it as model input.

Build the tables once. This is the long step. Set the variables in the shell that runs the jobs:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH=src
export PYSPARK_PYTHON="$PWD/.venv/bin/python"
export PYSPARK_DRIVER_PYTHON="$PWD/.venv/bin/python"
```

`$PWD` must be the repository root. If the workers use system Python 3.9, extract crashes with `PYTHON_VERSION_MISMATCH`.

```bash
.venv/bin/python -c "
from pathlib import Path
from musicrec.subset import load_medium_ids
ids = sorted(load_medium_ids('data/raw/fma_medium'))
Path('data/raw/medium_ids.csv').parent.mkdir(parents=True, exist_ok=True)
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

Run `run_neighbors.py` again after every `run_extract.py`. To time it on a different number of cores, pass the Spark master as the first argument, for example `.venv/bin/python jobs/run_neighbors.py "local[4]"`. `run_extract.py` prints `dim` at the end and it must be 75.

A copy of `data/processed/` skips the four jobs (about 37MB for the older 36-number tables, larger for 75). Its vectors must have 75 values to match the code. Playback still needs the mp3 files.

## Run

Two terminals, from the repository root. The API needs the same `PYTHONPATH` and `JAVA_HOME` as above, plus a JWT secret:

```bash
export MUSICREC_JWT_SECRET=dev-secret
.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

```bash
cd web && npm run dev -- --host 127.0.0.1 --port 5173
```

Open [http://localhost:5173](http://localhost:5173). Do not open `http://127.0.0.1:5173`. The page and the API must both use `localhost`, or the login cookie is not sent.

1. Register. The password must be at least 8 characters.
2. Log in before you open a track or For you.
3. Search, for example `love`, and open a track.
4. Similar is the precomputed neighbor list. For you should omit the track you just played.

Wait until the API log says it has started. The first start loads about 25,000 rows.

## Tests

From the repository root, outside a sandbox:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: 21 passed. The tests do not need the FMA download.

## Docs

| File | What it is |
|---|---|
| [docs/GUIDE.md](docs/GUIDE.md) | Full picture: idea, what is done, what is left, how similarity is defined |
| [docs/PLAN.md](docs/PLAN.md) | Original task list. Empty checkboxes are stale |
| [docs/updates/](docs/updates/) | Decisions after the plan: vector length (36, then 75), full medium set, data already built |

## Out of scope

No mood label on a track, no charts, no playlist editor, no cover art, no Spotify. Spark stays on the batch path.
