import numpy as np
import pandas as pd
import soundfile as sf

from musicrec.subset import build_subset, probe_audio


def test_build_subset_prefers_echonest_and_drops_empty_title():
    tracks = pd.DataFrame(
        {
            "track_id": [1, 2, 3, 4],
            "title": ["a", "b", "", "d"],
            "artist_name": ["aa", "bb", "cc", "dd"],
            "genre": ["Rock", "Pop", "Rock", "Jazz"],
        }
    )
    out = build_subset(tracks, echonest_ids={2, 4}, medium_ids={1, 2, 3, 4})
    assert list(out["track_id"]) == [2, 4, 1]
    assert list(out["has_echonest"]) == [True, True, False]


def test_build_subset_keeps_more_than_12000_tracks():
    ids = list(range(1, 12002))
    tracks = pd.DataFrame(
        {
            "track_id": ids,
            "title": ["t"] * len(ids),
            "artist_name": ["a"] * len(ids),
            "genre": ["Rock"] * len(ids),
        }
    )
    out = build_subset(tracks, echonest_ids=set(), medium_ids=set(ids))
    assert len(out) == 12001


def test_probe_audio_accepts_wav_and_rejects_missing(tmp_path):
    good = tmp_path / "000001.wav"
    sf.write(good, np.zeros(22050, dtype="float32"), 22050)
    assert probe_audio(good) is True
    assert probe_audio(tmp_path / "missing.wav") is False
