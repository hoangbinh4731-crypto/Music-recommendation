from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .db import ListeningHistory


def profile_vector(vectors, ranks):
    weights = np.array([1.0 / (1.0 + rank) for rank in ranks], dtype=float)
    matrix = np.vstack([np.asarray(vector, dtype=float) for vector in vectors])
    return (matrix * weights[:, None]).sum(axis=0) / weights.sum()


def _empty_tracks():
    return pd.DataFrame(columns=["track_id", "title", "artist_name", "genre", "has_echonest", "audio_path"])


class Catalog:
    def __init__(self, tracks, neighbor_rows, vectors):
        self.tracks = tracks if tracks is not None else _empty_tracks()
        self.by_id = {}
        for row in self.tracks.itertuples(index=False):
            self.by_id[int(row.track_id)] = row
        self.neighbors = {}
        for row in neighbor_rows.itertuples(index=False):
            pairs = []
            for neighbor_id, distance in zip(row.neighbor_ids, row.neighbor_distances):
                pairs.append((int(neighbor_id), float(distance)))
            self.neighbors[int(row.track_id)] = pairs
        self.vectors = {int(track_id): np.asarray(vector, dtype=float) for track_id, vector in vectors.items()}

    @classmethod
    def load(cls, processed_dir):
        tracks_path = processed_dir / "tracks.parquet"
        neighbors_path = processed_dir / "neighbors.parquet"
        features_path = processed_dir / "features.parquet"
        tracks = pd.read_parquet(tracks_path) if tracks_path.exists() else _empty_tracks()
        if neighbors_path.exists():
            neighbor_rows = pd.read_parquet(neighbors_path)
        else:
            neighbor_rows = pd.DataFrame(columns=["track_id", "neighbor_ids", "neighbor_distances"])
        vectors = {}
        if features_path.exists():
            features = pd.read_parquet(features_path)
            column = "vector" if "vector" in features.columns else None
            if column:
                for row in features.itertuples(index=False):
                    vectors[int(row.track_id)] = list(getattr(row, column))
        return cls(tracks, neighbor_rows, vectors)

    def search(self, query, limit=20):
        frame = self.tracks
        if query:
            needle = query.casefold()
            mask = frame["title"].fillna("").astype(str).str.casefold().str.contains(needle, regex=False) | frame[
                "artist_name"
            ].fillna("").astype(str).str.casefold().str.contains(needle, regex=False)
            frame = frame.loc[mask]
        frame = frame.sort_values("track_id").head(limit)
        return [self._public(int(track_id)) for track_id in frame["track_id"]]

    def _public(self, track_id):
        row = self.by_id[track_id]
        genre = row.genre
        if genre is None or (isinstance(genre, float) and np.isnan(genre)):
            genre = ""
        return {
            "track_id": int(track_id),
            "title": "" if row.title is None else str(row.title),
            "artist_name": "" if row.artist_name is None else str(row.artist_name),
            "genre": "" if genre is None else str(genre),
        }

    def audio_path(self, track_id):
        row = self.by_id.get(int(track_id))
        if row is None:
            return None
        return row.audio_path

    def content_neighbors(self, track_id):
        played = int(track_id)
        rows = []
        for neighbor_id, distance in self.neighbors.get(played, []):
            if neighbor_id == played or neighbor_id not in self.by_id:
                continue
            item = self._public(neighbor_id)
            item["distance"] = distance
            rows.append(item)
        return rows

    def record_play(self, session, user_id, track_id):
        session.add(
            ListeningHistory(
                user_id=int(user_id),
                track_id=int(track_id),
                played_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.commit()

    def history_ids(self, session, user_id):
        rows = (
            session.query(ListeningHistory)
            .filter(ListeningHistory.user_id == int(user_id))
            .order_by(ListeningHistory.played_at.desc(), ListeningHistory.id.desc())
            .all()
        )
        return [int(row.track_id) for row in rows]

    def recommend(self, history_ids, limit=20):
        ordered_catalog = sorted(self.by_id)
        if not history_ids:
            return [self._public(track_id) for track_id in ordered_catalog[:limit]]
        exclude = set(history_ids)
        vectors = []
        ranks = []
        for rank, track_id in enumerate(history_ids):
            if track_id in self.vectors:
                vectors.append(self.vectors[track_id])
                ranks.append(rank)
        if not vectors:
            return [self._public(track_id) for track_id in ordered_catalog if track_id not in exclude][:limit]
        profile = profile_vector(vectors, ranks)
        scored = []
        for track_id, vector in self.vectors.items():
            if track_id in exclude:
                continue
            scored.append((float(np.linalg.norm(profile - vector)), track_id))
        scored.sort()
        return [self._public(track_id) for _, track_id in scored[:limit]]
