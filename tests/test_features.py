import math

import numpy as np
import soundfile as sf

from musicrec.features import extract_track, raw_vector


def test_raw_vector_order_and_length():
    row = {
        "mfcc": list(range(20)),
        "chroma": list(range(12)),
        "tempo": 100.0,
        "spectral_centroid": 2000.0,
        "energy": 0.2,
        "zcr": 0.1,
    }
    vector = raw_vector(row)
    assert len(vector) == 36
    assert vector[:20] == list(range(20))
    assert vector[20:32] == list(range(12))
    assert vector[32:] == [100.0, 2000.0, 0.2, 0.1]


def test_extract_track_sine_is_finite(tmp_path):
    sr = 22050
    t = np.linspace(0, 1, sr, endpoint=False)
    y = 0.2 * np.sin(2 * np.pi * 440 * t).astype("float32")
    path = tmp_path / "sine.wav"
    sf.write(path, y, sr)
    row = extract_track(str(path), sr=sr)
    assert len(row["mfcc"]) == 20
    assert len(row["chroma"]) == 12
    values = row["mfcc"] + row["chroma"] + [
        row["tempo"],
        row["spectral_centroid"],
        row["energy"],
        row["zcr"],
    ]
    assert all(math.isfinite(v) for v in values)
