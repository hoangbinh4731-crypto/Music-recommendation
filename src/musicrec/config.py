from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "app.db"
SR = 22050
N_MFCC = 20
N_CHROMA = 12
N_SCALARS = 5  # centroid, rolloff, bandwidth, energy, zcr (mỗi cái có mean + std)
TOP_N = 20
LSH_BUCKET_LENGTH = 3.0
LSH_NUM_HASH_TABLES = 5
LSH_DISTANCE_THRESHOLD = 3.0
# mfcc mean+std, chroma mean+std, tempo, scalar mean+std
VECTOR_DIM = 2 * N_MFCC + 2 * N_CHROMA + 1 + 2 * N_SCALARS  # = 75
COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "lax"
COOKIE_SECURE = False
COOKIE_MAX_AGE = 604800
CORS_ORIGIN = "http://localhost:5173"
