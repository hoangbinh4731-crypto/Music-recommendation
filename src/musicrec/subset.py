from pathlib import Path

import librosa
import pandas as pd


def build_subset(tracks, echonest_ids, medium_ids):
    frame = tracks.loc[tracks["track_id"].isin(medium_ids)].copy()
    titles = frame["title"].fillna("").astype(str).str.strip()
    frame = frame.loc[titles != ""]
    frame["has_echonest"] = frame["track_id"].isin(set(echonest_ids))
    frame = frame.sort_values(
        by=["has_echonest", "track_id"],
        ascending=[False, True],
    )
    return frame.reset_index(drop=True)


def load_medium_ids(audio_root):
    ids = set()
    for path in Path(audio_root).rglob("*.mp3"):
        ids.add(int(path.stem))
    return ids


def load_flat_tracks(tracks_csv):
    tracks = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
    flat = pd.DataFrame(
        {
            "track_id": tracks.index.astype(int),
            "title": tracks[("track", "title")].values,
            "artist_name": tracks[("artist", "name")].values,
            "genre": tracks[("track", "genre_top")].values,
        }
    )
    return flat


def load_echonest_ids(echonest_csv):
    echonest = pd.read_csv(echonest_csv, index_col=0, header=[0, 1, 2])
    return set(int(i) for i in echonest.index)


def probe_audio(path, sr=22050):
    try:
        librosa.load(path, sr=sr, mono=True, duration=5)
    except Exception:
        return False
    return True


def medium_audio_path(audio_root, track_id):
    track_id = int(track_id)
    return Path(audio_root) / f"{track_id // 1000:03d}" / f"{track_id:06d}.mp3"


def split_playable(subset, audio_root, sr=22050):
    good_rows = []
    bad_rows = []
    for i, row in enumerate(subset.itertuples(index=False), start=1):
        path = medium_audio_path(audio_root, row.track_id)
        if probe_audio(path, sr=sr):
            good_rows.append({**row._asdict(), "audio_path": str(path)})
        else:
            reason = "missing" if not path.exists() else "unreadable"
            bad_rows.append({"track_id": int(row.track_id), "reason": reason})
        if i % 1000 == 0:
            print(f"probed={i} good={len(good_rows)} bad={len(bad_rows)}", flush=True)
    good = pd.DataFrame(good_rows)
    bad = pd.DataFrame(bad_rows, columns=["track_id", "reason"])
    return good, bad


def read_medium_ids_csv(path):
    ids = set()
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            ids.add(int(line))
    return ids
