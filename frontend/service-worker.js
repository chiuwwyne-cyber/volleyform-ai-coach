const CACHE_NAME = "volleyform-shell-v30";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./local-analyzer.js",
  "./pose-3d.js",
  "./config.js",
  "./manifest.webmanifest",
  "./assets/coach-header.png",
  "./assets/icon-192.png",
  "./assets/icon-512.png",
  "./assets/krunk-parts.json",
];

// App-shell files change often during development, so they must always be
// re-fetched when online; the cache is only a fallback for offline use.
// Large, rarely-changing binary assets (vendor libs, models, images) stay
// cache-first for speed and offline support.
const NETWORK_FIRST_SUFFIXES = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/local-analyzer.js",
  "/pose-3d.js",
  "/config.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
      ),
  );
  self.clients.claim();
});

function isNetworkFirst(pathname) {
  return NETWORK_FIRST_SUFFIXES.some((suffix) => pathname === suffix || pathname.endsWith(suffix));
}

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.includes("/api/")) {
    return;
  }

  if (isNetworkFirst(url.pathname)) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match("./index.html"))),
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        }),
    ),
  );
});
