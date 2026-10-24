import pandas as pd

from musicrec.neighbors import fill_short_lists, top_n_from_pairs


def test_top_n_keeps_nearest_one():
    pairs = pd.DataFrame(
        {
            "track_id": [1, 1],
            "neighbor_id": [2, 3],
            "distance": [0.1, 0.4],
        }
    )
    out = top_n_from_pairs(pairs, top_n=1)
    row = out.loc[out["track_id"] == 1].iloc[0]
    assert row["neighbor_ids"] == [2]
    assert row["neighbor_distances"] == [0.1]


def test_top_n_drops_self_and_sorts():
    pairs = pd.DataFrame(
        {
            "track_id": [1, 1, 1],
            "neighbor_id": [1, 3, 2],
            "distance": [0.0, 0.2, 0.5],
        }
    )
    out = top_n_from_pairs(pairs, top_n=2)
    row = out.loc[out["track_id"] == 1].iloc[0]
    assert 1 not in row["neighbor_ids"]
    assert row["neighbor_ids"] == [3, 2]
    assert row["neighbor_distances"] == [0.2, 0.5]


def test_fill_short_lists_adds_exact_neighbor_without_self():
    neighbors = pd.DataFrame(
        {
            "track_id": [1],
            "neighbor_ids": [[2]],
            "neighbor_distances": [[0.2]],
        }
    )
    features = pd.DataFrame(
        {
            "track_id": [1, 2, 3],
            "vector": [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
        }
    )
    out = fill_short_lists(neighbors, features, top_n=2, min_count=2)
    row = out.loc[out["track_id"] == 1].iloc[0]
    assert row["neighbor_ids"] == [2, 3]
    assert 1 not in row["neighbor_ids"]
    assert len(row["neighbor_ids"]) == 2
