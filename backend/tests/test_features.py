import io

import cv2
import numpy as np
import pytest
from PIL import Image
from skimage import data

from backend.app.pipelines import basic, geometry, oldphoto, redeye
from backend.app.services import colorize, faces, inpaint
from backend.tests.test_api import upload, wait

L = lambda a: np.asarray(a, dtype=np.float32) / 255


def _scratched():
    rng = np.random.default_rng(3)
    g = cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (300, 300), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    clean = np.repeat(g[..., None], 3, 2)
    bad = clean.copy()
    for x in (40, 120, 200, 260):
        y0 = int(rng.integers(0, 150))
        bad[y0 : y0 + 100, x : x + 1] = 0.95
    return clean, bad


def test_scratches_are_repaired_and_clean_photo_is_barely_touched():
    clean, bad = _scratched()
    out, frac = oldphoto.remove_damage(bad, 0.6)
    mask = bad.max(2) - clean.max(2) > 0.3
    assert frac > 0
    assert np.abs(out - clean)[mask].mean() < np.abs(bad - clean)[mask].mean() * 0.35  # rayones muy atenuados
    healthy = L(data.chelsea())
    same, _ = oldphoto.remove_damage(healthy, 0.6)
    assert np.abs(same - healthy).mean() < 0.0015  # una foto sana casi no cambia


def test_scratches_zero_is_identity():
    _, bad = _scratched()
    assert np.array_equal(oldphoto.remove_damage(bad, 0.0)[0], bad)


def test_geometry():
    img = L(data.coffee())  # 400x600
    assert geometry.transform(img, 90).shape[:2] == (600, 400)
    assert geometry.transform(img, 180).shape == img.shape
    assert np.array_equal(geometry.transform(img, 90)[0, 0], img[-1, 0])  # 90° horario: esquina inf-izq pasa a sup-izq
    r = geometry.transform(img, 0, 8)
    assert r.shape[0] < 400 and r.shape[1] < 600 and abs(r.shape[1] / r.shape[0] - 1.5) < 0.02  # recorta bordes vacíos, misma proporción
    assert geometry.transform(img, 0, 0, (0.25, 0.25, 0.5, 0.5)).shape[:2] == (200, 300)
    with pytest.raises(Exception):
        geometry.transform(img, 0, 0, (0.8, 0.8, 0.5, 0.5))


def test_shadows_lift_dark_areas_more_than_bright():
    img = L(data.chelsea()) * 0.5
    out = basic.shadows_highlights(img, 0.8, 0.0)
    assert out.mean() > img.mean() + 0.01
    assert np.array_equal(basic.shadows_highlights(img, 0, 0), img)


@pytest.mark.skipif(not colorize.available(), reason="modelo de colorización no instalado")
def test_colorize_adds_chroma_and_keeps_luminance():
    col = L(data.coffee())
    gray = np.repeat(cv2.cvtColor((col * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)[..., None], 3, 2).astype(np.float32) / 255
    out = colorize.get_colorizer().colorize(gray)
    lab = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
    assert np.abs(lab[..., 1:] - 128).mean() > 5  # ya no es gris
    l_in = cv2.cvtColor(gray, cv2.COLOR_RGB2LAB)[..., 0]
    assert np.abs(lab[..., 0] - l_in).mean() < 3  # luminancia conservada


@pytest.mark.skipif(not inpaint.available(), reason="modelo de borrado no instalado")
def test_inpaint_changes_only_masked_area():
    img = L(data.coffee())
    mask = np.zeros(img.shape[:2], np.uint8)
    mask[200:280, 250:330] = 1
    out = inpaint.get_inpainter().remove(img, mask)
    far = cv2.dilate(mask, np.ones((31, 31), np.uint8)) == 0
    assert np.abs(out - img)[far].max() == 0  # fuera de la zona marcada NO cambia ni un píxel
    assert np.abs(out - img)[mask > 0].mean() > 0.01  # dentro sí
    with pytest.raises(Exception):
        inpaint.get_inpainter().remove(img, np.zeros_like(mask))


def test_red_eye_neutralizes_only_red_pixels():
    img = L(data.astronaut())
    boxes = faces.detect_faces(img)
    x, y, w, h = boxes[0]
    assert np.array_equal(redeye.fix_red_eye(img, boxes)[0], img)  # sin ojos rojos no cambia nada
    painted = img.copy()
    pupils = np.zeros(img.shape[:2], np.uint8)
    for cx in (x + int(w * 0.3), x + int(w * 0.7)):  # pupilas rojas pintadas sobre los ojos
        cv2.circle(painted, (cx, y + int(h * 0.38)), max(3, w // 14), (0.85, 0.1, 0.1), -1)
        cv2.circle(pupils, (cx, y + int(h * 0.38)), max(3, w // 14), 1, -1)
    out, n = redeye.fix_red_eye(painted, boxes)
    assert n >= 1
    redness = lambda a: (a[..., 0] - np.maximum(a[..., 1], a[..., 2]))[pupils > 0].mean()
    assert redness(out) < redness(painted) * 0.4  # el rojo de las pupilas baja mucho
    outside = cv2.dilate(pupils, np.ones((25, 25), np.uint8)) == 0
    assert np.abs(out - painted)[outside].max() == 0  # nada cambia lejos de los ojos


def _png(arr):
    b = io.BytesIO()
    Image.fromarray((arr * 255).astype(np.uint8)).save(b, "PNG")
    return b.getvalue()


def test_transform_and_inpaint_endpoints_create_new_images(client):
    up = upload(client, _png(L(data.coffee())), "c.png").json()
    r = client.post(f"/api/images/{up['id']}/transform", json={"rotate": 90, "crop": {"x": 0, "y": 0, "w": 0.5, "h": 0.5}})
    assert r.status_code == 200
    new = r.json()
    assert new["id"] != up["id"] and (new["width"], new["height"]) == (200, 300)
    assert client.get(f"/api/images/{up['id']}").json()["width"] == 600  # la anterior sigue intacta
    assert client.post(f"/api/images/{up['id']}/transform", json={"crop": {"x": 0.9, "y": 0, "w": 0.5, "h": 1}}).status_code == 400
    if inpaint.available():
        m = np.zeros((400, 600), np.uint8)
        m[200:280, 250:330] = 255
        mb = io.BytesIO()
        Image.fromarray(m).save(mb, "PNG")
        r = client.post(f"/api/images/{up['id']}/inpaint", files={"mask": ("m.png", mb.getvalue(), "image/png")})
        assert r.status_code == 200 and r.json()["id"] != up["id"]
        assert client.post(f"/api/images/{up['id']}/inpaint", files={"mask": ("m.png", b"nope", "image/png")}).status_code == 415


def test_tiff_and_heic_accepted(client):
    arr = (L(data.chelsea())[:120, :160] * 255).astype(np.uint8)
    tif = io.BytesIO()
    Image.fromarray(arr).save(tif, "TIFF")
    r = upload(client, tif.getvalue(), "a.tif")
    assert r.status_code == 200 and r.json()["format"] == "TIFF"
    from backend.app.services.image_io import HEIC_OK

    if HEIC_OK:
        heic = io.BytesIO()
        Image.fromarray(arr).save(heic, "HEIF")
        r = upload(client, heic.getvalue(), "a.heic")
        assert r.status_code == 200 and r.json()["format"] == "HEIF"


def test_job_with_new_options_and_validation(client):
    up = upload(client, _png(L(data.astronaut())[:200, :200]), "x.png").json()
    ok = client.post("/api/jobs", json={"image_id": up["id"], "upscale": False, "scratches": 0.5, "shadows": 0.4, "highlights": 0.2, "redeye": True}).json()
    assert wait(client, ok["id"])["status"] == "done"
    assert client.post("/api/jobs", json={"image_id": up["id"], "shadows": 3}).status_code == 422
