import pandas as pd
from fastapi.testclient import TestClient

from api.db import ListeningHistory, open_session
from api.main import create_app


def write_catalog(processed, tracks, neighbors):
    processed.mkdir(parents=True)
    pd.DataFrame(tracks).to_parquet(processed / "tracks.parquet", index=False)
    pd.DataFrame(neighbors).to_parquet(processed / "neighbors.parquet", index=False)


def make_client(tmp_path, monkeypatch, tracks, neighbors):
    processed = tmp_path / "processed"
    write_catalog(processed, tracks, neighbors)
    monkeypatch.setenv("MUSICREC_JWT_SECRET", "test-secret")
    monkeypatch.setenv("MUSICREC_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("MUSICREC_PROCESSED_DIR", str(processed))
    return TestClient(create_app())


def test_search_artist_casefold_and_cap(tmp_path, monkeypatch):
    tracks = [
        {
            "track_id": index,
            "title": f"song {index}",
            "artist_name": "Band",
            "genre": "Rock",
            "has_echonest": False,
            "audio_path": f"/tmp/{index}.mp3",
        }
        for index in range(1, 26)
    ]
    client = make_client(tmp_path, monkeypatch, tracks, {"track_id": [], "neighbor_ids": [], "neighbor_distances": []})
    found = client.get("/tracks/search", params={"q": "bAnD"})
    assert found.status_code == 200
    body = found.json()
    assert len(body) == 20
    assert body[0]["artist_name"] == "Band"
    assert [row["track_id"] for row in body] == list(range(1, 21))


def test_play_records_history_and_drops_self_neighbor(tmp_path, monkeypatch):
    audio = tmp_path / "000001.mp3"
    audio.write_bytes(b"not-audio")
    tracks = [
        {
            "track_id": 1,
            "title": "one",
            "artist_name": "a",
            "genre": "Rock",
            "has_echonest": False,
            "audio_path": str(audio),
        },
        {
            "track_id": 2,
            "title": "two",
            "artist_name": "b",
            "genre": "Pop",
            "has_echonest": False,
            "audio_path": str(tmp_path / "missing.mp3"),
        },
    ]
    neighbors = {
        "track_id": [1],
        "neighbor_ids": [[1, 2]],
        "neighbor_distances": [[0.0, 0.4]],
    }
    client = make_client(tmp_path, monkeypatch, tracks, neighbors)
    client.post("/auth/register", json={"username": "ada", "password": "password1"})
    client.post("/auth/login", json={"username": "ada", "password": "password1"})
    played = client.post("/play/1")
    assert played.status_code == 200
    assert [row["track_id"] for row in played.json()["neighbors"]] == [2]
    session = open_session(tmp_path / "app.db")
    rows = session.query(ListeningHistory).all()
    assert len(rows) == 1
    assert rows[0].track_id == 1
    session.close()
