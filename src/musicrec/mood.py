import pandas as pd


def zscore(series):
    mean = float(series.mean())
    std = float(series.std(ddof=0))
    if std == 0.0:
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def scores(df):
    out = df.copy()
    out["arousal"] = 0.5 * zscore(out["tempo"]) + 0.5 * zscore(out["energy"])
    out["valence"] = 0.5 * zscore(out["spectral_centroid"]) - 0.5 * zscore(out["zcr"])
    return out
