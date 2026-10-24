import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.catalog import profile_vector
from api.main import create_app


def test_profile_vector_weights():
    profile = profile_vector([[0.0, 0.0], [2.0, 0.0]], [0, 1])
    assert np.allclose(profile, [2.0 / 3.0, 0.0])


def _client(tmp_path, monkeypatch, track_count, vectors):
    processed = tmp_path / "processed"
    processed.mkdir()
    tracks = pd.DataFrame(
        {
            "track_id": list(range(1, track_count + 1)),
            "title": [f"t{i}" for i in range(1, track_count + 1)],
            "artist_name": ["a"] * track_count,
            "genre": ["Rock"] * track_count,
            "has_echonest": [False] * track_count,
            "audio_path": [str(tmp_path / f"{i}.mp3") for i in range(1, track_count + 1)],
        }
    )
    tracks.to_parquet(processed / "tracks.parquet", index=False)
    pd.DataFrame(
        {
            "track_id": list(vectors),
            "vector": list(vectors.values()),
        }
    ).to_parquet(processed / "features.parquet", index=False)
    monkeypatch.setenv("MUSICREC_JWT_SECRET", "test-secret")
    monkeypatch.setenv("MUSICREC_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("MUSICREC_PROCESSED_DIR", str(processed))
    client = TestClient(create_app())
    client.post("/auth/register", json={"username": "ada", "password": "password1"})
    client.post("/auth/login", json={"username": "ada", "password": "password1"})
    return client


def test_history_recommend_excludes_played(tmp_path, monkeypatch):
    client = _client(
        tmp_path,
        monkeypatch,
        3,
        {1: [0.0, 0.0], 2: [0.0, 0.0], 3: [10.0, 0.0]},
    )
    assert client.post("/play/1").status_code == 200
    body = client.get("/recommend/history")
    ids = [row["track_id"] for row in body.json()]
    assert 1 not in ids
    assert ids[0] == 2


def test_empty_history_returns_first_20_ids(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, 25, {1: [0.0]})
    body = client.get("/recommend/history")
    assert [row["track_id"] for row in body.json()] == list(range(1, 21))
