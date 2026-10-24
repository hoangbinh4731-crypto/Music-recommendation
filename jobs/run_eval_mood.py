import json

import pandas as pd

from musicrec.config import PROCESSED_DIR, RAW_DIR
from musicrec.mood import scores


def pearson(left, right):
    value = left.corr(right)
    if pd.isna(value):
        return None
    return float(value)


def build_report(features, echonest):
    joined = features.merge(echonest, on="track_id", how="inner")
    scored = scores(joined)
    return {
        "n": int(len(scored)),
        "arousal_pearson": pearson(scored["arousal"], scored["echonest_energy"]),
        "valence_pearson": pearson(scored["valence"], scored["echonest_valence"]),
    }


def load_echonest(path):
    frame = pd.read_csv(path, index_col=0, header=[0, 1, 2])
    return pd.DataFrame(
        {
            "track_id": frame.index.astype(int),
            "echonest_energy": frame[("echonest", "audio_features", "energy")].to_numpy(),
            "echonest_valence": frame[("echonest", "audio_features", "valence")].to_numpy(),
        }
    )


def main():
    raw = pd.read_parquet(PROCESSED_DIR / "features_raw.parquet")
    tracks = pd.read_parquet(PROCESSED_DIR / "tracks.parquet")
    keep = tracks.loc[tracks["has_echonest"], "track_id"]
    raw = raw.loc[raw["track_id"].isin(set(keep))]
    report = build_report(raw, load_echonest(RAW_DIR / "fma_metadata" / "echonest.csv"))
    out = PROCESSED_DIR / "mood_report.json"
    out.write_text(json.dumps(report))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
