import pandas as pd


def top_n_from_pairs(pairs, top_n):
    frame = pairs.loc[pairs["track_id"] != pairs["neighbor_id"]].copy()
    frame = frame.sort_values(["track_id", "distance", "neighbor_id"])
    rows = []
    for track_id, group in frame.groupby("track_id", sort=True):
        head = group.head(top_n)
        rows.append(
            {
                "track_id": int(track_id),
                "neighbor_ids": [int(value) for value in head["neighbor_id"]],
                "neighbor_distances": [float(value) for value in head["distance"]],
            }
        )
    return pd.DataFrame(rows, columns=["track_id", "neighbor_ids", "neighbor_distances"])


def fill_short_lists(neighbors, features, top_n, min_count=5):
    import numpy as np

    vectors = {
        int(row.track_id): np.asarray(row.vector, dtype=float)
        for row in features.itertuples(index=False)
    }
    current = {}
    for row in neighbors.itertuples(index=False):
        current[int(row.track_id)] = (
            [int(value) for value in row.neighbor_ids],
            [float(value) for value in row.neighbor_distances],
        )
    rows = []
    for track_id in sorted(vectors):
        ids, dists = current.get(track_id, ([], []))
        ids = list(ids)
        dists = list(dists)
        if len(ids) < min_count:
            origin = vectors[track_id]
            ranked = []
            for other_id, vec in vectors.items():
                if other_id == track_id or other_id in ids:
                    continue
                ranked.append((float(np.linalg.norm(origin - vec)), other_id))
            ranked.sort()
            for dist, other_id in ranked:
                if len(ids) >= top_n:
                    break
                ids.append(other_id)
                dists.append(dist)
        rows.append(
            {
                "track_id": track_id,
                "neighbor_ids": ids[:top_n],
                "neighbor_distances": dists[:top_n],
            }
        )
    return pd.DataFrame(rows)
