import os

os.environ.setdefault("MUSICREC_JWT_SECRET", "test-secret")
os.environ.setdefault("MUSICREC_DB_PATH", "/tmp/musicrec-pytest.db")
