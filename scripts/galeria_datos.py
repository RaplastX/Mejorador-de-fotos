"""Genera casos de prueba reproducibles (imágenes libres de scikit-image, degradadas a propósito), los procesa con el
pipeline real y guarda pares antes/después + métricas. Uso: python scripts/galeria_datos.py CARPETA_SALIDA"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2, numpy as np
from PIL import Image
from skimage import data
from skimage.metrics import peak_signal_noise_ratio as psnr, structural_similarity as ssim
from backend.app.pipelines import enhance

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
u8 = lambda a: (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)

def jpeg(a, q):
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(u8(a), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.cvtColor(cv2.imdecode(buf, 1), cv2.COLOR_BGR2RGB).astype(np.float32) / 255

def down(a, w): h = round(a.shape[0] * w / a.shape[1]); return cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)

ast = data.astronaut().astype(np.float32) / 255
cat = data.chelsea().astype(np.float32) / 255
cof = data.coffee().astype(np.float32) / 255
page = np.repeat(data.page()[..., None], 3, 2).astype(np.float32) / 255

def old_photo(a):
    g = a.mean(2, keepdims=True); g = 0.55 + (g - g.mean()) * 0.55
    sep = np.concatenate([g * 1.04, g * 0.95, g * 0.80], 2) + rng.normal(0, 0.035, a.shape)
    for _ in range(14):  # rayones
        x = rng.integers(0, a.shape[1]); y0 = rng.integers(0, a.shape[0] - 80); sep[y0:y0 + rng.integers(30, 120), x:x + 1] += 0.25
    return jpeg(np.clip(sep, 0, 1), 55)

cases = [
    dict(id="retrato", titulo="Retrato de baja resolución", desc="Foto de 256 px muy comprimida (JPEG calidad 35), como un retrato reenviado por mensajería. Ajustes: superresolución 4× + restauración facial 60 % + piel suave.",
         truth=ast, degrade=lambda t: jpeg(down(t, 256), 35), opts=dict(target="original", scale=4.0, faces=True, face_strength=0.6, skin=True, skin_smooth=0.3, skin_wrinkles=0.3)),
    dict(id="retrato_sr", titulo="El mismo retrato SIN restauración facial", desc="Solo superresolución 4×. Compara con el caso anterior para ver qué aporta cada función (la IA general deforma ojos y boca cuando falta información).",
         truth=ast, degrade=lambda t: jpeg(down(t, 256), 35), opts=dict(target="original", scale=4.0)),
    dict(id="antigua", titulo="Foto antigua deteriorada", desc="Retrato desvaído, con ruido y rayones simulados. Ajustes: limpieza de rayones 50 % + 4× + restauración facial 50 %.",
         truth=ast, degrade=lambda t: old_photo(down(t, 300)), opts=dict(target="original", scale=4.0, faces=True, face_strength=0.5, scratches=0.5)),
    dict(id="antigua_color", titulo="Foto antigua, rayones y colorización", desc="La misma foto antigua, ahora con color generado por IA (DDColor). Los colores son una suposición plausible, no los reales. Ajustes: rayones 50 % + colorizar + 4× + rostro 50 %.",
         truth=ast, degrade=lambda t: old_photo(down(t, 300)), opts=dict(target="original", scale=4.0, faces=True, face_strength=0.5, scratches=0.5, colorize=True), colorful=True),
    dict(id="gato", titulo="Foto con poca luz y ruido", desc="Gato subexpuesto con ruido de sensor. Ajustes: intensidad intensa, sin ampliar (1×) para ver solo ruido/exposición/color.",
         truth=cat, degrade=lambda t: np.clip(np.power(t, 1.9) * 0.9 + rng.normal(0, 0.035, t.shape), 0, 1).astype(np.float32), opts=dict(intensity="intensa", upscale=False)),
    dict(id="cafe", titulo="Naturaleza muerta pequeña", desc="Imagen de 300 px de ancho ampliada 4× (superresolución general, sin rostros).",
         truth=cof, degrade=lambda t: jpeg(down(t, 300), 60), opts=dict(target="original", scale=4.0)),
    dict(id="texto", titulo="Texto y líneas finas (caso difícil)", desc="Página escaneada pequeña y comprimida, ampliada 4×. Es un caso donde la IA puede inventar trazos: no la uses para leer texto dudoso.",
         truth=page, degrade=lambda t: jpeg(down(t, 330), 50), opts=dict(target="original", scale=4.0)),
]
def spoon_mask(shape):
    m = np.zeros(shape[:2], np.uint8)
    cv2.ellipse(m, (365, 285), (44, 48), 0, 0, 360, 1, -1)                       # cuenco de la cuchara
    cv2.line(m, (368, 245), (420, 78), 1, 22)                                    # mango
    return m

meta = []
for c in cases:
    src = c["degrade"](c["truth"]).astype(np.float32)
    if c.get("colorful"): pass
    t0 = time.time()
    res = enhance.run(src, enhance.Options(**c["opts"]), lambda p, s: None, lambda: False)
    dt = time.time() - t0
    H, W = res.shape[:2]
    bic = cv2.resize(src, (W, H), interpolation=cv2.INTER_CUBIC)
    ref = cv2.resize(c["truth"], (W, H), interpolation=cv2.INTER_AREA if c["truth"].shape[1] > W else cv2.INTER_CUBIC)
    m = {}
    for name, im in (("bicubica", bic), ("luma", res)):
        m[name] = dict(psnr=round(float(psnr(ref, np.clip(im, 0, 1), data_range=1)), 2), ssim=round(float(ssim(ref, np.clip(im, 0, 1), channel_axis=2, data_range=1)), 4))
    Image.fromarray(u8(bic)).save(out / f"{c['id']}_antes.jpg", quality=88)  # "antes" = ampliación bicúbica estándar al mismo tamaño
    Image.fromarray(u8(res)).save(out / f"{c['id']}_despues.jpg", quality=88)
    Image.fromarray(u8(src)).save(out / f"{c['id']}_entrada.png")
    meta.append(dict(id=c["id"], titulo=c["titulo"], desc=c["desc"], entrada=f"{src.shape[1]}×{src.shape[0]}", salida=f"{W}×{H}", segundos=round(dt, 1), metricas=m))
    print(c["id"], meta[-1]["entrada"], "->", meta[-1]["salida"], f"{dt:.1f}s", m)
# --- Borrar objetos (LaMa): el "antes" es la foto original, no una ampliación
from backend.app.services import inpaint
if inpaint.available():
    t0 = time.time(); res = inpaint.get_inpainter().remove(cof, spoon_mask(cof.shape)); dt = time.time() - t0
    shown = u8(cof).copy(); mk = spoon_mask(cof.shape).astype(bool)
    Image.fromarray(u8(cof)).save(out / "objeto_antes.jpg", quality=90); Image.fromarray(u8(res)).save(out / "objeto_despues.jpg", quality=90)
    far = cv2.dilate(spoon_mask(cof.shape), np.ones((41, 41), np.uint8)) == 0
    meta.append(dict(id="objeto", titulo="Borrar un objeto", desc="Se marcó la cuchara con una máscara y LaMa rellenó el hueco. Solo cambia el área marcada.", entrada=f"{cof.shape[1]}×{cof.shape[0]}", salida=f"{cof.shape[1]}×{cof.shape[0]}",
        segundos=round(dt, 1), metricas=None, antes_label="Original", despues_label="Sin la cuchara", extra=f"Píxeles que cambian lejos de la máscara: {int((np.abs(res - cof).max(2) > 0)[far].sum())}"))
(out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
