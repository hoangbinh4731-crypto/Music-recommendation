import pandas as pd

from musicrec.mood import scores


def test_scores_match_hand_zscores():
    frame = pd.DataFrame(
        {
            "tempo": [0.0, 0.0, 2.0, 2.0],
            "energy": [0.0, 2.0, 0.0, 2.0],
            "spectral_centroid": [0.0, 0.0, 0.0, 0.0],
            "zcr": [0.0, 0.0, 0.0, 0.0],
        }
    )
    out = scores(frame)
    assert out["arousal"].tolist() == [-1.0, 0.0, 0.0, 1.0]
    assert out["valence"].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_scores_zero_std_is_zero():
    frame = pd.DataFrame(
        {
            "tempo": [3.0, 3.0, 3.0],
            "energy": [1.0, 1.0, 1.0],
            "spectral_centroid": [4.0, 4.0, 4.0],
            "zcr": [2.0, 2.0, 2.0],
        }
    )
    out = scores(frame)
    assert out["arousal"].tolist() == [0.0, 0.0, 0.0]
    assert out["valence"].tolist() == [0.0, 0.0, 0.0]
