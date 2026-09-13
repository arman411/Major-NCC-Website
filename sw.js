/**
 * NCC Portal — Enhanced Service Worker v2.0
 * Upgrade 1: Offline-first caching + Background Sync for form submissions
 */

const CACHE_NAME = 'ncc-portal-v2.0';
const STATIC_CACHE = 'ncc-static-v2.0';
const API_CACHE = 'ncc-api-v2.0';

// Core pages to cache immediately on install
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/pages/notices.html',
  '/pages/gallery.html',
  '/pages/about.html',
  '/pages/activities.html',
  '/pages/achievements.html',
  '/pages/contact.html',
  '/pages/enrollment.html',
  '/pages/login.html',
  '/css/style.css',
  '/js/main.js',
  '/js/api.js',
  '/js/dark-mode.js',
  '/js/pro-effects.js',
  '/js/animations-3d.js',
  '/js/search-modal.js',
  '/js/offline-sync.js',
  '/images/ncc_badge.png',
  '/manifest.json',
  '/pages/offline.html'
];

// Install: pre-cache critical resources
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Pre-caching critical resources');
      // Cache each URL individually so one failure doesn't block all
      return Promise.allSettled(
        PRECACHE_URLS.map(url => cache.add(url).catch(e => console.warn(`[SW] Failed to cache ${url}:`, e)))
      );
    })
  );
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then((keys) =>
        Promise.all(
          keys
            .filter(key => key !== CACHE_NAME && key !== STATIC_CACHE && key !== API_CACHE)
            .map(key => {
              console.log('[SW] Deleting old cache:', key);
              return caches.delete(key);
            })
        )
      )
    ])
  );
});

// Fetch: smart caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests, cross-origin, and browser extensions
  if (request.method !== 'GET' || !url.origin.includes(location.origin)) return;

  // API requests: Network-first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request, API_CACHE, 30));
    return;
  }

  // Static assets (CSS, JS, images, fonts): Cache-first
  if (
    url.pathname.match(/\.(css|js|png|jpg|jpeg|gif|webp|svg|woff|woff2|ttf|ico)$/)
  ) {
    event.respondWith(cacheFirstWithNetwork(request, STATIC_CACHE));
    return;
  }

  // HTML pages: Network-first with offline fallback
  event.respondWith(networkFirstWithOfflineFallback(request));
});

async function networkFirstWithCache(request, cacheName, maxAgeSeconds) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: true, message: 'You are offline', offline: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function cacheFirstWithNetwork(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (e) {
    return new Response('Resource unavailable offline', { status: 503 });
  }
}

async function networkFirstWithOfflineFallback(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Return offline page
    const offlinePage = await caches.match('/pages/offline.html');
    return offlinePage || new Response('<h1>You are offline</h1><p>Please reconnect to continue.</p>', {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Background Sync: Replay queued form submissions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-forms') {
    event.waitUntil(replayQueuedRequests());
  }
});

async function replayQueuedRequests() {
  // Notify all clients to process their IndexedDB queues
  const clients = await self.clients.matchAll();
  clients.forEach(client => {
    client.postMessage({ type: 'REPLAY_QUEUE' });
  });
}

// Push Notifications (existing functionality preserved)
self.addEventListener('push', (event) => {
  let data = { title: 'NCC GPH Hamirpur', body: 'New update available!', url: '/' };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (e) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/images/ncc_badge.png',
      badge: '/images/ncc_badge.png',
      vibrate: [200, 100, 200],
      tag: 'ncc-notification',
      data: { url: data.url || '/' }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
