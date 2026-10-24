# 003 Dataset and JDK 17 are installed

Date: 2026-09-26

Overrides: Task 1 Step 4 ("Do not install Java yourself"), Task 2 ("Do not download `fma_medium.zip` in this task" and "track_count <= 12000"), and the ~10-12k architecture note. Update 002 already removed the 12,000 cap. This file records what is actually on disk.

## Installed

Checked 2026-09-26:

- `data/raw/fma_medium/` — 25,000 mp3 files, 156 folders (`000`–`155`), about 23GB. Full medium set. Not cropped.
- `data/raw/fma_medium.zip` — 23,825,005,356 bytes. Keep it. macOS `unzip` cannot read it (`need PK compat. v4.6`). It was extracted with `tar -xf`.
- `data/raw/fma_metadata/` — about 1.4GB. `tracks.csv` and `echonest.csv` are present. Same `tar` extract. `features.csv` is in that folder for comparison only. Do not use it as model input.
- `data/raw/fma_metadata.zip` — 358,412,441 bytes.
- JDK 17.0.20.1 via Homebrew `openjdk@17`. It is keg-only. `java` on `PATH` is still Java 26, and Spark 3.5.4 fails on 26 (`Subject.getSubject`). Jobs must use:

```
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
```

Mirror: `https://os.unil.cloud.switch.ch/fma/`. It drops connections. Resume a partial zip with HTTP range requests. Do not trust `stat` size on `fma_medium.zip` alone: the downloader truncated it to the full length while it was still sparse. A chunk is missing when its first 4KB are all zeros.

Audio path: `data/raw/fma_medium/{id//1000:03d}/{id:06d}.mp3`.

## Already written, not run on this data

Code lives under `music-recommendation/`. Python 3.11 venv is `.venv`. Unit tests passed without the real audio. `data/processed/` does not exist. These jobs have not been run:

1. `jobs/run_subset.py` on the full medium id set. Drop empty titles only. No 12,000 cap. `VECTOR_DIM` is 36 (update 001).
2. `jobs/run_extract.py`
3. `jobs/run_neighbors.py`
4. `jobs/run_eval_mood.py`

FastAPI and the Vite app exist. `data/app.db` is from a local auth smoke test. Search returns nothing until Parquet exists. Mood stays out of the UI.

## Next session

Open the repo that contains `music-recommendation/`, not the parent folder. The parent is not a git repo. Read `docs/PLAN.md`, then updates `001`, `002`, and this file. Do not commit unless asked.
