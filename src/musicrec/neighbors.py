import numpy as np
import pandas as pd


def top_n_from_pairs(pairs, top_n):
    frame = pairs.loc[pairs["track_id"] != pairs["neighbor_id"]].copy()
    frame = frame.sort_values(["track_id", "distance", "neighbor_id"])
    frame = frame.drop_duplicates(["track_id", "neighbor_id"], keep="first")
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
    track_ids = np.array([int(v) for v in features["track_id"]], dtype=np.int64)
    matrix = np.vstack([np.asarray(v, dtype=float) for v in features["vector"]])
    order = np.argsort(track_ids)
    track_ids = track_ids[order]
    matrix = matrix[order]

    current = {}
    for row in neighbors.itertuples(index=False):
        current[int(row.track_id)] = (
            [int(v) for v in row.neighbor_ids],
            [float(v) for v in row.neighbor_distances],
        )

    rows = []
    for i, track_id in enumerate(track_ids):
        track_id = int(track_id)
        ids, dists = current.get(track_id, ([], []))
        ids = list(ids)
        dists = list(dists)
        if len(ids) < min_count:
            d = np.linalg.norm(matrix - matrix[i], axis=1)
            exclude = np.isin(track_ids, ids)
            exclude[i] = True
            cand = np.flatnonzero(~exclude)
            ranked = cand[np.lexsort((track_ids[cand], d[cand]))]
            for j in ranked:
                if len(ids) >= top_n:
                    break
                ids.append(int(track_ids[j]))
                dists.append(float(d[j]))
        rows.append(
            {
                "track_id": track_id,
                "neighbor_ids": ids[:top_n],
                "neighbor_distances": dists[:top_n],
            }
        )
    return pd.DataFrame(rows)
