const CACHE = "daily-enrichment-v2";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", (e) => {
  // index.html can be served with caching headers that make a plain fetch()/addAll() silently pick up
  // a stale copy from the browser's HTTP cache even under a brand-new CACHE name. Force a real
  // network round-trip for every asset so a version bump always ships what's actually on the server.
  e.waitUntil(
    caches.open(CACHE).then((c) =>
      Promise.all(ASSETS.map((url) => fetch(url, { cache: "reload" }).then((res) => c.put(url, res))))
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});
