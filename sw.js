/* NCC GPH Service Worker v4 — Network-first for pages & scripts */
const CACHE_NAME = 'ncc-gph-v4';

// Only cache external fonts & icons (truly static)
const IMMUTABLE_ASSETS = [
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(IMMUTABLE_ASSETS).catch(() => {})
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => caches.delete(k))) // Delete ALL old caches (v1, v2, v3, etc.)
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never intercept API calls
  if (url.port === '5000' || url.port === '8000' || url.pathname.startsWith('/api/')) return;

  // External fonts/icons → cache-first
  if (url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
    event.respondWith(
      caches.match(event.request).then(
        (cached) => cached || fetch(event.request).then((res) => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(event.request, clone));
          }
          return res;
        }).catch(() => new Response('Offline', { status: 503 }))
      )
    );
    return;
  }

  // Local pages, scripts, CSS → NETWORK-FIRST (always get fresh code)
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        // If we got a successful network response, save a copy in the cache
        if (res && res.status === 200 && event.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
