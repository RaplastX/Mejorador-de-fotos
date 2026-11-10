// Service worker: carcasa de la app + modelo y runtime de IA para uso SIN CONEXIÓN. Nunca cachea /api ni fotos.
const CACHE = "luma-shell-v2";
const PRECACHE = ["/", "/icons/icon-192.png", "/manifest.webmanifest"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE).catch(() => undefined))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;
  const heavy = u.pathname.startsWith("/models/") || u.pathname.startsWith("/ort/") || u.pathname.startsWith("/assets/");
  e.respondWith(heavy
    ? caches.match(e.request).then((hit) => hit || fetch(e.request).then((r) => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); } return r; }))
    : fetch(e.request).then((r) => { if (r.ok && e.request.mode === "navigate") { const copy = r.clone(); caches.open(CACHE).then((c) => c.put("/", copy)); } return r; }).catch(() => caches.match(e.request).then((hit) => hit || caches.match("/"))));
});
