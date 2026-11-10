// Sirve el sitio estático desde KV (los ficheros están comprimidos con gzip). Sin dependencias.
const TYPES = {
  html: "text/html; charset=utf-8", js: "text/javascript; charset=utf-8", mjs: "text/javascript; charset=utf-8", css: "text/css; charset=utf-8",
  wasm: "application/wasm", onnx: "application/octet-stream", json: "application/json", webmanifest: "application/manifest+json",
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", svg: "image/svg+xml", ico: "image/x-icon", txt: "text/plain; charset=utf-8",
};
const SECURITY = {
  // Aislamiento de origen cruzado: habilita los hilos WASM (SharedArrayBuffer). 'credentialless' deja pasar Google Fonts.
  "Cross-Origin-Opener-Policy": "same-origin", "Cross-Origin-Embedder-Policy": "credentialless",
  "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};

export default {
  async fetch(req, env) {
    if (req.method !== "GET" && req.method !== "HEAD") return new Response("Método no permitido", { status: 405 });
    const url = new URL(req.url);
    let key = decodeURIComponent(url.pathname.slice(1));
    if (!key || key.endsWith("/")) key += "index.html";
    let body = await env.ASSETS.get(key, { type: "stream" });
    let ext = (key.split(".").pop() || "").toLowerCase();
    if (!body) {
      // Rutas sin fichero: la app es de una sola página (también responde a /api/* con HTML, y la app lo interpreta como «sin servidor»).
      if (/\.[a-z0-9]+$/i.test(key) && !url.pathname.startsWith("/api/")) return new Response("No encontrado", { status: 404, headers: SECURITY });
      body = await env.ASSETS.get("index.html", { type: "stream" });
      ext = "html";
      if (!body) return new Response("Sitio no desplegado", { status: 503 });
    }
    const hashed = key.startsWith("assets/") || key.startsWith("ort/") || key.startsWith("models/") || key.startsWith("samples/") || key.startsWith("icons/");
    const headers = {
      ...SECURITY,
      "Content-Type": TYPES[ext] || "application/octet-stream",
      "Content-Encoding": "gzip", "Vary": "Accept-Encoding",
      "Cache-Control": (hashed ? "public, max-age=31536000, immutable" : "no-cache") + ", no-transform",
    };
    // encodeBody "manual": el cuerpo YA está en gzip; sin esto Cloudflare lo recomprime (zstd/br) y el navegador recibe basura.
    return new Response(req.method === "HEAD" ? null : body, { headers, encodeBody: "manual" });
  },
};
