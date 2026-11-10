import hashlib
import io
import time

import pytest
from PIL import Image

from backend.app.core.config import settings
from backend.tests.conftest import make_image


def upload(client, data, name="foto.jpg"):
    return client.post("/api/images", files={"file": (name, data, "application/octet-stream")})


def wait(client, jid, timeout=120):
    t = time.time()
    while time.time() - t < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] in ("done", "error", "cancelled"):
            return j
        time.sleep(0.2)
    raise TimeoutError


def test_system_is_local_and_private(client):
    j = client.get("/api/system").json()
    assert j["privacy"] == {"local_only": True, "telemetry": False, "host": "127.0.0.1"}
    from backend.app.services import face_restore

    assert j["features"]["face_restoration"] is face_restore.available()  # solo se anuncia lo que existe de verdad
    assert j["features"]["inpainting"] is False  # aún no implementado


def test_rejects_invalid_and_unsupported(client):
    assert upload(client, b"esto no es una imagen").status_code == 415
    assert upload(client, b"").status_code == 400
    gif = io.BytesIO()
    Image.new("RGB", (8, 8)).save(gif, "GIF")
    assert upload(client, gif.getvalue()).status_code == 415
    # extensión engañosa: el contenido real manda
    assert upload(client, b"MZ\x90\x00 ejecutable", "virus.jpg").status_code == 415


def test_rejects_oversized_pixels(client, monkeypatch):
    monkeypatch.setattr(settings, "max_input_pixels", 1000)
    r = upload(client, make_image())
    assert r.status_code == 413


def test_rejects_foreign_host(client):
    r = client.get("/api/system", headers={"host": "evil.example.com"})
    assert r.status_code == 400


def test_bad_ids_are_refused(client):
    assert client.get("/api/images/..%2F..%2Fetc%2Fpasswd/display").status_code in (400, 404)
    assert client.get("/api/jobs/not-a-valid-id").status_code == 400


@pytest.mark.parametrize("fmt,name", [("JPEG", "a.jpg"), ("PNG", "a.png"), ("WEBP", "a.webp")])
def test_full_flow_formats_and_original_untouched(client, fmt, name):
    data = make_image(fmt)
    digest = hashlib.sha256(data).hexdigest()
    up = upload(client, data, name).json()
    assert (up["width"], up["height"]) == (160, 120)
    assert "analysis" in up
    req = {"image_id": up["id"], "target": "original", "scale": 2}
    job = client.post("/api/jobs", json=req).json()
    done = wait(client, job["id"])
    assert done["status"] == "done", done
    assert done["result"] == {"width": 320, "height": 240}
    # el original no cambia
    from backend.app.services.store import get_store

    store = get_store()
    assert hashlib.sha256(store.original_path(store.get_image(up["id"])).read_bytes()).hexdigest() == digest
    for out_fmt in ("jpeg", "png", "webp"):
        r = client.post(f"/api/jobs/{job['id']}/export", json={"format": out_fmt})
        assert r.status_code == 200
        assert Image.open(io.BytesIO(r.content)).size == (320, 240)


def test_target_resolutions(client):
    up = upload(client, make_image(size=(480, 270))).json()
    for target, w in (("1080p", 1920), ("4k", 3840)):
        p = client.post("/api/plan", json={"image_id": up["id"], "target": target}).json()
        assert p["width"] == w and p["height"] == round(270 * w / 480)
        assert p["generative"] is True and p["warnings"]


def test_output_limit_enforced(client, monkeypatch):
    up = upload(client, make_image(size=(480, 270))).json()
    monkeypatch.setattr(settings, "max_output_pixels", 100_000)
    assert client.post("/api/plan", json={"image_id": up["id"], "target": "4k"}).status_code == 400


def test_export_strips_gps_by_default(client):
    up = upload(client, make_image(exif=True)).json()
    job = client.post("/api/jobs", json={"image_id": up["id"], "upscale": False}).json()
    assert wait(client, job["id"])["status"] == "done"
    clean = Image.open(io.BytesIO(client.post(f"/api/jobs/{job['id']}/export", json={"format": "jpeg"}).content))
    assert not clean.getexif()
    keep = Image.open(io.BytesIO(client.post(f"/api/jobs/{job['id']}/export", json={"format": "jpeg", "keep_metadata": True}).content))
    assert keep.getexif().get(0x010F) == "TestCam" and not keep.getexif().get_ifd(0x8825)
    gps = Image.open(io.BytesIO(client.post(f"/api/jobs/{job['id']}/export", json={"format": "jpeg", "keep_metadata": True, "keep_gps": True}).content))
    assert gps.getexif().get_ifd(0x8825)


def test_alpha_preserved_in_png(client):
    up = upload(client, make_image("PNG", mode="RGBA"), "t.png").json()
    job = client.post("/api/jobs", json={"image_id": up["id"], "upscale": False}).json()
    assert wait(client, job["id"])["status"] == "done"
    out = Image.open(io.BytesIO(client.post(f"/api/jobs/{job['id']}/export", json={"format": "png"}).content))
    assert out.mode == "RGBA"


def test_cancel_job(client):
    up = upload(client, make_image(size=(1200, 900))).json()
    job = client.post("/api/jobs", json={"image_id": up["id"], "target": "original", "scale": 4}).json()
    client.delete(f"/api/jobs/{job['id']}")
    assert wait(client, job["id"])["status"] == "cancelled"


def test_delete_image_removes_files(client):
    up = upload(client, make_image()).json()
    from backend.app.services.store import get_store

    d = get_store().get_image(up["id"]).dir
    assert d.exists()
    assert client.delete(f"/api/images/{up['id']}").status_code == 204
    assert not d.exists()
    assert client.get(f"/api/images/{up['id']}/display").status_code == 404


def test_unknown_api_route_is_json_404_not_html(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404 and r.json()["error"] == "not_found"


def test_spa_fallback_cannot_read_outside_dist(client):
    r = client.get("/..%2f..%2fetc%2fpasswd")
    assert "root:" not in r.text
