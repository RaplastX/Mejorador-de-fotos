import time

import numpy as np
import pytest
from PIL import Image
from skimage import data

from backend.app.models.upscaler import get_upscaler  # noqa: F401
from backend.app.pipelines import enhance, skin
from backend.app.services import face_restore, faces
from backend.tests.test_api import upload, wait

needs_faces = pytest.mark.skipif(not face_restore.available(), reason="modelos de rostros no instalados")


def _portrait():
    return data.astronaut().astype(np.float32) / 255  # dominio público (NASA)


def test_skin_retouch_keeps_tone_and_outside_face_untouched():
    img = _portrait()
    boxes = faces.detect_faces(img)
    assert boxes
    out = skin.retouch(img, boxes, 0.8, 0.8, True)
    x, y, w, h = boxes[0]
    outside = np.ones(img.shape[:2], bool)
    outside[max(0, y - int(w * 0.5)) : y + h + int(w * 0.5), max(0, x - int(w * 0.5)) : x + w + int(w * 0.5)] = False
    assert np.abs(out - img)[outside].max() == 0  # nada fuera del entorno del rostro
    # el tono medio de la cara no cambia (la capa base no se toca)
    face = (slice(y, y + h), slice(x, x + w))
    assert np.abs(out[face].mean((0, 1)) - img[face].mean((0, 1))).max() < 0.02
    # y hay un cambio real (suavizado)
    assert np.abs(out[face] - img[face]).mean() > 0.002


def test_skin_zero_is_identity():
    img = _portrait()
    assert np.array_equal(skin.retouch(img, faces.detect_faces(img), 0.0, 0.0), img)


def test_keep_texture_preserves_more_detail():
    img = _portrait()
    b = faces.detect_faces(img)
    x, y, w, h = b[0]
    lap = lambda a: np.abs(a[y : y + h, x : x + w, 1] - __import__("cv2").GaussianBlur(a[y : y + h, x : x + w, 1], (0, 0), 1.2)).mean()
    keep = lap(skin.retouch(img, b, 1.0, 0.0, True))
    flat = lap(skin.retouch(img, b, 1.0, 0.0, False))
    assert keep > flat


@needs_faces
def test_face_restoration_changes_face_and_exclusion_protects_it():
    small = np.asarray(Image.fromarray((_portrait() * 255).astype(np.uint8)).resize((256, 256)), dtype=np.float32) / 255
    f = lambda **k: enhance.run(small, enhance.Options(upscale=False, **k), lambda p, s: None, lambda: False)
    base = f(faces=False)
    on = np.abs(f(faces=True, face_strength=1.0) - base).mean()
    box = faces.detect_faces(small)[0]
    off = np.abs(f(faces=True, face_strength=1.0, exclude_faces=(box,)) - base).mean()
    assert on > 0.003 and off < on * 0.3


@needs_faces
def test_face_job_through_api(client):
    buf = __import__("io").BytesIO()
    Image.fromarray(data.astronaut()).save(buf, "JPEG", quality=70)
    up = upload(client, buf.getvalue()).json()
    assert up["faces"]
    job = client.post("/api/jobs", json={"image_id": up["id"], "upscale": False, "faces": True, "face_strength": 0.6, "skin": True}).json()
    done = wait(client, job["id"], timeout=180)
    assert done["status"] == "done", done
