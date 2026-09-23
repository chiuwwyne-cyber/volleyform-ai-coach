const CACHE_NAME = "volleyform-shell-v110-0f33961e";
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

// Large binaries the analysis needs but the shell does not: the MediaPipe
// models and wasm runtime, plus the vendored libraries. Until now these were
// only cached the first time they were fetched (cache-first at runtime), so a
// user who installed the PWA and went offline BEFORE ever running one analysis
// found the models had never been downloaded and analysis failed offline. They
// are pre-cached on install now, best-effort (see below) so the first offline
// run works. Kept separate from APP_SHELL because a missing entry here must not
// fail the whole install, and because these are ~55 MB that need not gate it.
const PRECACHE_ASSETS = [
  "./models/pose_landmarker_full.task",
  "./models/pose_landmarker_lite.task",
  "./models/hand_landmarker.task",
  "./vendor/mediapipe/vision_bundle.mjs",
  "./vendor/mediapipe/wasm/vision_wasm_internal.js",
  "./vendor/mediapipe/wasm/vision_wasm_internal.wasm",
  "./vendor/mediapipe/wasm/vision_wasm_module_internal.js",
  "./vendor/mediapipe/wasm/vision_wasm_module_internal.wasm",
  "./vendor/mediapipe/wasm/vision_wasm_nosimd_internal.js",
  "./vendor/mediapipe/wasm/vision_wasm_nosimd_internal.wasm",
  "./vendor/three/three.module.min.js",
  "./vendor/qrcode/qrcode.js",
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
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // APP_SHELL is required (all-or-nothing); the large assets are best-effort
      // (individual cache.add under allSettled) so one missing path cannot break
      // the install and leave the app with no service worker.
      const shell = cache.addAll(APP_SHELL);
      return shell.then(() =>
        Promise.allSettled(PRECACHE_ASSETS.map((asset) => cache.add(asset))),
      );
    }),
  );
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
  // runtime-share.json is per-session launcher state: it holds the CURRENT
  // cloudflare tunnel / LAN address, which changes every time the launcher
  // runs. Caching it would make the QR code hand out a dead tunnel from an
  // earlier session, so it bypasses the worker entirely like /api/ does.
  // (The page requests it with cache: "no-store", but that only governs the
  // HTTP cache -- the service worker still intercepts unless excluded here.)
  if (
    url.origin !== self.location.origin ||
    url.pathname.includes("/api/") ||
    url.pathname.endsWith("/runtime-share.json")
  ) {
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
