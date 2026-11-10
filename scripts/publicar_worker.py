"""Publica el sitio estático (frontend/dist) en Cloudflare con un Worker + KV, gratis y sin Pages.
Usa las credenciales de Cloudflare del entorno (CLOUDFLARE_ACCOUNT_ID y el token/proxy de api.cloudflare.com).

  python scripts/publicar_worker.py --site RUTA_DEL_SITIO --confirmo-publico [--name luma-enhance]

El sitio será PÚBLICO en https://<name>.<tu-subdominio>.workers.dev (no contiene secretos ni datos de usuario).
Por qué no Pages: la subida de ficheros de Pages usa un token temporal propio que el proxy de este entorno sustituye."""
import argparse, gzip, json, os, subprocess, sys, tempfile, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def curl(method, url, *, data=None, headers=(), files=()):
    cmd = ["curl", "-sS", "-m", "300", "-X", method, url]
    for h in headers:
        cmd += ["-H", h]
    if data is not None:
        cmd += ["--data-binary", f"@{data}" if isinstance(data, Path) else data]
    for f in files:
        cmd += ["-F", f]
    out = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except Exception:
        return {"success": False, "errors": [out.stdout[:200] or out.stderr[:200]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--name", default="luma-enhance")
    ap.add_argument("--solo-worker", action="store_true", help="solo redesplegar el Worker, sin resubir los ficheros")
    ap.add_argument("--confirmo-publico", action="store_true", help="confirma que quieres publicar un sitio PÚBLICO")
    a = ap.parse_args()
    if not a.confirmo_publico:
        sys.exit("Esto publica un sitio PÚBLICO. Repite con --confirmo-publico si es lo que quieres.")
    acc = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}"
    site = Path(a.site)

    lst = curl("GET", f"{base}/storage/kv/namespaces?per_page=100")
    ns = next((n["id"] for n in lst.get("result", []) if n["title"] == f"{a.name}-assets"), None)
    if not ns:
        r = curl("POST", f"{base}/storage/kv/namespaces", data=json.dumps({"title": f"{a.name}-assets"}), headers=["Content-Type: application/json"])
        ns = (r.get("result") or {}).get("id") or sys.exit(f"No se pudo crear KV: {r}")
    print("KV:", ns)

    files = [] if a.solo_worker else [p for p in site.rglob("*") if p.is_file() and p.name not in ("_headers", "sw.js")]
    with tempfile.TemporaryDirectory() as tmp:
        for p in sorted(files):
            key = p.relative_to(site).as_posix()
            gz = Path(tmp) / "f.gz"
            gz.write_bytes(gzip.compress(p.read_bytes(), 9))
            r = curl("PUT", f"{base}/storage/kv/namespaces/{ns}/values/{urllib.parse.quote(key, safe='')}", data=gz, headers=["Content-Type: application/octet-stream"])
            print(f"  {'OK ' if r.get('success') else 'ERR'} {key} ({p.stat().st_size // 1024} KB → {gz.stat().st_size // 1024} KB)")
            if not r.get("success"):
                sys.exit(f"Falló la subida de {key}: {r.get('errors')}")
    # sw.js no se publica: el service worker se reintroducirá cuando el Worker sirva sus cabeceras de caché de forma verificada.

    meta = {"main_module": "worker.js", "compatibility_date": "2026-11-01", "bindings": [{"type": "kv_namespace", "name": "ASSETS", "namespace_id": ns}]}
    r = curl("PUT", f"{base}/workers/scripts/{a.name}", files=[f"metadata={json.dumps(meta)};type=application/json", f"worker.js=@{ROOT / 'cloudflare' / 'worker.js'};filename=worker.js;type=application/javascript+module"])
    print("Worker:", r.get("success"), r.get("errors"))
    if not r.get("success"):
        sys.exit(1)
    r = curl("POST", f"{base}/workers/scripts/{a.name}/subdomain", data=json.dumps({"enabled": True, "previews_enabled": False}), headers=["Content-Type: application/json"])
    sub = (curl("GET", f"{base}/workers/subdomain").get("result") or {}).get("subdomain")
    print("workers.dev activado:", r.get("success"), r.get("errors"))
    print(f"\nSitio: https://{a.name}.{sub}.workers.dev")


if __name__ == "__main__":
    main()
