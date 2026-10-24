from fastapi.testclient import TestClient

from api.main import create_app


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICREC_JWT_SECRET", "test-secret")
    monkeypatch.setenv("MUSICREC_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("MUSICREC_PROCESSED_DIR", str(tmp_path / "processed"))
    return TestClient(create_app())


def test_register_login_cookie_and_logout(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    registered = client.post("/auth/register", json={"username": "ada", "password": "password1"})
    assert registered.status_code == 200

    logged_in = client.post("/auth/login", json={"username": "ada", "password": "password1"})
    assert logged_in.status_code == 200
    assert logged_in.json() == {"username": "ada"}
    assert "token" not in logged_in.json()
    cookie = logged_in.headers["set-cookie"]
    assert "access_token" in cookie
    assert "httponly" in cookie.lower()

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "ada"

    logged_out = client.post("/auth/logout")
    assert logged_out.status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_short_password_and_duplicate_username(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    short = client.post("/auth/register", json={"username": "ada", "password": "short"})
    assert short.status_code == 422
    client.post("/auth/register", json={"username": "ada", "password": "password1"})
    again = client.post("/auth/register", json={"username": "ada", "password": "password1"})
    assert again.status_code == 409
