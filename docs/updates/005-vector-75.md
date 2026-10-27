# 005 Vector length is 75

Date: 2026-10-27

Overrides: update 001 (`VECTOR_DIM = 36`) for new runs. Update 004 stays true for the
run of 2026-09-26, which produced 36-dim data.

Feature set is extended. Per track the vector is: MFCC mean (20), MFCC std (20), chroma
mean (12), chroma std (12), tempo (1), and five scalar features (spectral centroid,
rolloff, bandwidth, RMS energy, zero-crossing rate), each with mean and std (10).
That is 75 values. `config.VECTOR_DIM` is derived from these constants.

The 36-dim outputs are kept in `data/processed_36/` for comparison. `data/processed/`
holds 75-dim outputs once `run_extract.py` and `run_neighbors.py` are rerun.

Other changes:
- `features.py` reads a 30 s window from the middle of each track; silent or non-finite
  audio is rejected. `feature_names()` and `scalar_columns()` added.
- `features_raw.parquet` holds `track_id` and `raw` (75 values). `scalar_columns` recovers
  tempo, energy, spectral_centroid, zcr for the mood scores.
- `run_extract.py` prints dim, seconds per track and core count.
- `run_neighbors.py` takes the Spark master as argv[1], picks top-N inside Spark, prints
  the fallback rate, and asserts the feature dimension matches `VECTOR_DIM`.
- LSH parameters (bucket 3.0, 5 tables, threshold 3.0) are a first guess for 75 dims.
  Retune against runtime and the fallback rate.
- `api/catalog.py` reads only `track_id` and `vector` from `features.parquet`.
- `tests/test_features.py` rewritten for 75 dims.

Run order: `run_extract.py`, `run_neighbors.py`, `run_eval_mood.py`.
Rerun `run_neighbors.py` after every `run_extract.py`.
