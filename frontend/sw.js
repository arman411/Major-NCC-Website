/**
 * sw.js – Service Worker for NCC GPH PWA
 * Caches static assets for offline-first experience
 */
const CACHE_NAME = 'ncc-gph-v1';
const STATIC_ASSETS = [
  '/',
  '/frontend/index.html',
  '/frontend/css/style.css',
  '/frontend/js/main.js',
  '/frontend/js/pro-effects.js',
  '/frontend/images/ncc_badge.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (!event.request.url.startsWith(self.location.origin)) return;
  if (event.request.url.includes('/api/')) return; // Don't cache API calls
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).catch(() => caches.match('/'));
    })
  );
});
