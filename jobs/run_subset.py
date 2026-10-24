import argparse
import json
from pathlib import Path

import pandas as pd

from musicrec.config import PROCESSED_DIR
from musicrec.subset import (
    build_subset,
    load_echonest_ids,
    load_flat_tracks,
    read_medium_ids_csv,
    split_playable,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--medium-ids-csv", required=True, type=Path)
    parser.add_argument("--audio-root", type=Path)
    parser.add_argument("--out", type=Path, default=PROCESSED_DIR / "subset_manifest.json")
    args = parser.parse_args()

    tracks = load_flat_tracks(args.metadata / "tracks.csv")
    echonest_ids = load_echonest_ids(args.metadata / "echonest.csv")
    medium_ids = read_medium_ids_csv(args.medium_ids_csv)
    subset = build_subset(tracks, echonest_ids, medium_ids)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "track_count": int(len(subset)),
        "echonest_count": int(subset["has_echonest"].sum()) if len(subset) else 0,
        "track_ids": [int(i) for i in subset["track_id"].tolist()],
    }
    args.out.write_text(json.dumps(payload))
    print(f"track_count={payload['track_count']} echonest_count={payload['echonest_count']}")

    if args.audio_root is None:
        return
    good, bad = split_playable(subset, args.audio_root)
    processed = args.out.parent
    bad.to_csv(processed / "bad_tracks.csv", index=False)
    if good.empty:
        good = pd.DataFrame(
            columns=["track_id", "title", "artist_name", "genre", "has_echonest", "audio_path"]
        )
    good.to_parquet(processed / "tracks.parquet", index=False)
    print(f"bad_tracks={len(bad)} playable={len(good)}")


if __name__ == "__main__":
    main()
