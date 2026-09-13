/**
 * NCC Portal Frontend — Enhanced Service Worker v2.0
 * Mirrors root sw.js for the /frontend/ static directory
 */

const CACHE_NAME = 'ncc-frontend-v2.0';
const STATIC_ASSETS = [
  '/frontend/',
  '/frontend/index.html',
  '/frontend/css/style.css',
  '/frontend/js/main.js',
  '/frontend/js/api.js',
  '/frontend/js/dark-mode.js',
  '/frontend/js/pro-effects.js',
  '/frontend/js/animations-3d.js',
  '/frontend/js/offline-sync.js',
  '/frontend/pages/notices.html',
  '/frontend/pages/gallery.html',
  '/frontend/pages/about.html',
  '/frontend/pages/offline.html',
  '/frontend/manifest.json'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      Promise.allSettled(STATIC_ASSETS.map(url =>
        cache.add(url).catch(e => console.warn('[SW-Frontend] Could not cache:', url, e))
      ))
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then(keys =>
        Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
      )
    ])
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;
  
  // Cache-first for static assets
  if (url.pathname.match(/\.(css|js|png|jpg|jpeg|gif|webp|svg|woff2|ttf|ico)$/)) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(res => {
        if (res.ok) caches.open(CACHE_NAME).then(c => c.put(request, res.clone()));
        return res;
      }))
    );
    return;
  }

  // Network-first for HTML pages
  event.respondWith(
    fetch(request)
      .then(res => {
        if (res.ok) caches.open(CACHE_NAME).then(c => c.put(request, res.clone()));
        return res;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        const offlinePage = await caches.match('/frontend/pages/offline.html');
        return offlinePage || new Response('<h1>Offline</h1>', { headers: { 'Content-Type': 'text/html' } });
      })
  );
});

self.addEventListener('push', (event) => {
  let data = { title: 'NCC GPH Hamirpur', body: 'New update!', url: '/' };
  try { if (event.data) data = { ...data, ...event.data.json() }; } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/frontend/images/ncc_badge.png',
      badge: '/frontend/images/ncc_badge.png',
      data: { url: data.url }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.openWindow(url));
});
