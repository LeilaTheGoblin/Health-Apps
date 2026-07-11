const CACHE = "workout-tracker-v11";
const ASSETS = [
          "./",
          "./index.html",
          "./manifest.json",
          "./icon-192.png",
          "./icon-512.png"
        ];

self.addEventListener("install", (e) => {
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
