import numpy as np

from backend.app.models.upscaler import get_upscaler
from backend.app.pipelines import basic
from backend.app.services import image_io


def test_tiling_has_no_seams_vs_single_pass():
    rng = np.random.default_rng(0)
    img = np.clip(np.linspace(0, 1, 96)[None, :, None] * np.ones((96, 1, 3)) + rng.normal(0, 0.02, (96, 96, 3)), 0, 1).astype(np.float32)
    up = get_upscaler()
    whole = up.upscale(img, tile=256)
    tiled = up.upscale(img, tile=32, overlap=16)
    assert whole.shape == (384, 384, 3)
    assert np.abs(whole - tiled).max() < 0.02  # solape suficiente → sin costuras visibles


def test_basic_ops_keep_range_and_shape():
    rng = np.random.default_rng(1)
    img = rng.random((64, 64, 3), dtype=np.float32)
    for fn in (basic.denoise, basic.auto_color, basic.sharpen):
        out = fn(img, 0.7)
        assert out.shape == img.shape and out.min() >= 0 and out.max() <= 1
        assert np.array_equal(fn(img, 0.0), img)  # intensidad 0 = sin cambios


def test_safe_names():
    assert image_io.safe_stem("../../etc/passwd") == "passwd"
    assert image_io.safe_stem("mi foto (1).jpg") == "mi_foto_1"
    assert image_io.unique_name("a", "jpg", {"a_mejorada.jpg"}) == "a_mejorada_2.jpg"
