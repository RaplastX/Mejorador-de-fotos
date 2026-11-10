import pytest
from fastapi.testclient import TestClient

from backend.app.core import auth
from backend.app.core.config import settings
from backend.app.main import create_app


@pytest.fixture()
def remote(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "remote", True)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(create_app(), base_url="http://192.168.1.50:8765") as c:
        yield c


def test_remote_requires_pairing(remote):
    assert remote.get("/api/system").status_code == 401
    assert remote.get("/pair?t=falso").status_code == 401
    assert remote.get("/manifest.webmanifest").status_code in (200, 404)  # público (404 solo si no hay dist)
    tok = auth.get_token()
    assert oct(settings.token_file.stat().st_mode & 0o777) == "0o600"
    r = remote.get(f"/pair?t={tok}", follow_redirects=False)
    assert r.status_code == 303 and "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower()
    assert remote.get("/api/system").status_code == 200  # la cookie quedó guardada


def test_cookie_not_accepted_with_wrong_value(remote):
    remote.cookies.set(auth.COOKIE, "otro")
    assert remote.get("/api/system").status_code == 401


def test_local_mode_has_no_auth_but_rejects_foreign_host(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "remote", False)
    monkeypatch.setattr(settings, "data_dir", tmp_path)  # aislado: el cierre de la app borra sesiones
    with TestClient(create_app(), base_url="http://localhost") as c:
        assert c.get("/api/system").status_code == 200
        assert c.get("/api/system", headers={"host": "evil.example"}).status_code == 400
