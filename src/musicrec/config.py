from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "app.db"
SR = 22050
N_MFCC = 20
N_CHROMA = 12
TOP_N = 20
LSH_BUCKET_LENGTH = 2.0
LSH_NUM_HASH_TABLES = 4
LSH_DISTANCE_THRESHOLD = 2.0
VECTOR_DIM = 36
COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "lax"
COOKIE_SECURE = False
COOKIE_MAX_AGE = 604800
CORS_ORIGIN = "http://localhost:5173"
