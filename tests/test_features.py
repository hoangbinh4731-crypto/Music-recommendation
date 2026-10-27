import math

import numpy as np
import pytest
import soundfile as sf

from musicrec.config import VECTOR_DIM
from musicrec.features import (
    SCALARS,
    extract_track,
    feature_names,
    raw_vector,
    scalar_columns,
)


def make_row():
    row = {
        "mfcc": [float(i) for i in range(20)],
        "mfcc_std": [float(100 + i) for i in range(20)],
        "chroma": [float(200 + i) for i in range(12)],
        "chroma_std": [float(300 + i) for i in range(12)],
        "tempo": 100.0,
    }
    for k, name in enumerate(SCALARS):
        row[name] = 1000.0 + k
        row[name + "_std"] = 2000.0 + k
    return row


def test_raw_vector_order_and_length():
    vector = raw_vector(make_row())
    assert len(vector) == 75
    assert len(vector) == VECTOR_DIM == len(feature_names())
    assert vector[:20] == [float(i) for i in range(20)]
    assert vector[20:40] == [float(100 + i) for i in range(20)]
    assert vector[40:52] == [float(200 + i) for i in range(12)]
    assert vector[52:64] == [float(300 + i) for i in range(12)]
    assert vector[64] == 100.0
    # 5 đặc trưng vô hướng, mỗi cái xen kẽ mean rồi std
    assert vector[65:] == [
        1000.0, 2000.0, 1001.0, 2001.0, 1002.0, 2002.0, 1003.0, 2003.0, 1004.0, 2004.0
    ]


def test_feature_names_unique_and_aligned():
    names = feature_names()
    assert len(names) == len(set(names)) == VECTOR_DIM
    assert names[0] == "mfcc1"
    assert names[64] == "tempo"
    assert names[65] == "spectral_centroid"


def test_raw_vector_rejects_nan():
    row = make_row()
    row["tempo"] = float("nan")
    with pytest.raises(ValueError):
        raw_vector(row)


def test_scalar_columns_recovers_raw_values():
    import pandas as pd

    raw = pd.Series([raw_vector(make_row())])
    out = scalar_columns(raw)
    assert out.loc[0, "tempo"] == 100.0
    assert out.loc[0, "spectral_centroid"] == 1000.0
    assert out.loc[0, "energy"] == 1003.0
    assert out.loc[0, "zcr"] == 1004.0


def test_extract_track_sine_is_finite(tmp_path):
    sr = 22050
    t = np.linspace(0, 1, sr, endpoint=False)
    y = 0.2 * np.sin(2 * np.pi * 440 * t).astype("float32")
    path = tmp_path / "sine.wav"
    sf.write(path, y, sr)
    row = extract_track(str(path), sr=sr)
    assert len(row["mfcc"]) == len(row["mfcc_std"]) == 20
    assert len(row["chroma"]) == len(row["chroma_std"]) == 12
    vector = raw_vector(row)
    assert len(vector) == VECTOR_DIM
    assert all(math.isfinite(v) for v in vector)


def test_extract_track_silence_is_rejected(tmp_path):
    sr = 22050
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(sr, dtype="float32"), sr)
    with pytest.raises(ValueError):
        extract_track(str(path), sr=sr)
