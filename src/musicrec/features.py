import numpy as np
import librosa
import librosa.feature.rhythm as rhythm

N_MFCC = 20
SCALARS = ["spectral_centroid", "spectral_rolloff", "spectral_bandwidth",
           "energy", "zcr"]


def _load_middle(path, sr, duration):
    total = librosa.get_duration(path=path)
    offset = max(0.0, total / 2 - duration / 2)
    y, sr = librosa.load(path, sr=sr, mono=True, offset=offset, duration=duration)
    return y, sr


def extract_track(path, sr=22050, duration=30.0):
    y, sr = _load_middle(path, sr, duration)
    if y.size == 0 or np.max(np.abs(y)) < 1e-6:
        raise ValueError(f"Audio rỗng hoặc im lặng: {path}")

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    energy = librosa.feature.rms(y=y)
    zcr = librosa.feature.zero_crossing_rate(y)

    out = {
        "mfcc": mfcc.mean(axis=1).tolist(),
        "mfcc_std": mfcc.std(axis=1).tolist(),
        "chroma": chroma.mean(axis=1).tolist(),
        "chroma_std": chroma.std(axis=1).tolist(),
        "tempo": float(rhythm.tempo(y=y, sr=sr)[0]),
    }
    for name, mat in zip(SCALARS, [centroid, rolloff, bandwidth, energy, zcr]):
        out[name] = float(mat.mean())
        out[name + "_std"] = float(mat.std())
    return out


def feature_names():
    names = [f"mfcc{i+1}" for i in range(N_MFCC)]
    names += [f"mfcc{i+1}_std" for i in range(N_MFCC)]
    names += [f"chroma{i+1}" for i in range(12)]
    names += [f"chroma{i+1}_std" for i in range(12)]
    names += ["tempo"]
    for s in SCALARS:
        names += [s, s + "_std"]
    return names


def raw_vector(row):
    vec = (list(row["mfcc"]) + list(row["mfcc_std"])
           + list(row["chroma"]) + list(row["chroma_std"])
           + [row["tempo"]])
    for s in SCALARS:
        vec += [row[s], row[s + "_std"]]
    vec = [float(v) for v in vec]
    if not np.all(np.isfinite(vec)):
        raise ValueError("Vector có NaN/Inf")
    return vec
