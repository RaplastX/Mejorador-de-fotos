import io
import os
import tempfile

import numpy as np
import pytest
from PIL import Image

_tmp = tempfile.mkdtemp(prefix="luma-test-")
os.environ["LUMA_DATA_DIR"] = _tmp

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app(), base_url="http://localhost") as c:
        yield c


def make_image(fmt="JPEG", size=(160, 120), mode="RGB", exif=False) -> bytes:
    rng = np.random.default_rng(1)
    base = np.linspace(0, 255, size[0], dtype=np.uint8)[None, :, None].repeat(size[1], 0).repeat(3, 2)
    noise = rng.integers(0, 25, base.shape, dtype=np.uint8)
    arr = np.clip(base.astype(int) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    if mode == "RGBA":
        img = img.convert("RGBA")
        img.putalpha(Image.fromarray((np.indices(size[::-1]).sum(0) % 255).astype(np.uint8)))
    buf = io.BytesIO()
    kw = {}
    if exif:
        e = Image.Exif()
        e[0x010F] = "TestCam"
        e.get_ifd(0x8825)[1] = "N"  # GPS
        e[0x0112] = 1
        kw["exif"] = e.tobytes()
    img.save(buf, fmt, **kw)
    return buf.getvalue()
