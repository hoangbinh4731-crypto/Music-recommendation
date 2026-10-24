import librosa
import librosa.feature.rhythm as rhythm


def extract_track(path, sr=22050):
    y, sr = librosa.load(path, sr=sr, mono=True)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20).mean(axis=1)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)
    tempo = float(rhythm.tempo(y=y, sr=sr)[0])
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    energy = float(librosa.feature.rms(y=y).mean())
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())
    return {
        "mfcc": mfcc.astype("float64").tolist(),
        "chroma": chroma.astype("float64").tolist(),
        "tempo": tempo,
        "spectral_centroid": centroid,
        "energy": energy,
        "zcr": zcr,
    }


def raw_vector(row):
    return (
        [float(value) for value in row["mfcc"]]
        + [float(value) for value in row["chroma"]]
        + [
            float(row["tempo"]),
            float(row["spectral_centroid"]),
            float(row["energy"]),
            float(row["zcr"]),
        ]
    )
