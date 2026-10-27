import os
import tempfile

os.environ.setdefault("MUSICREC_JWT_SECRET", "test-secret")
os.environ.setdefault(
    "MUSICREC_DB_PATH", os.path.join(tempfile.gettempdir(), "musicrec-pytest.db")
)
