/**
 * offline-sync.js — IndexedDB-based offline form queue + sync manager
 * Upgrade 1: Background Sync and offline indicator
 */

(function () {
  'use strict';

  const DB_NAME = 'ncc-offline-queue';
  const STORE_NAME = 'pending-requests';
  let db = null;

  // ── IndexedDB Setup ──────────────────────────────────────────────
  function openDB() {
    return new Promise((resolve, reject) => {
      if (db) return resolve(db);
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = (e) => {
        const store = e.target.result.createObjectStore(STORE_NAME, {
          keyPath: 'id', autoIncrement: true
        });
        store.createIndex('status', 'status', { unique: false });
      };
      req.onsuccess = (e) => { db = e.target.result; resolve(db); };
      req.onerror = () => reject(req.error);
    });
  }

  async function queueRequest(endpoint, method, data) {
    const database = await openDB();
    return new Promise((resolve, reject) => {
      const tx = database.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).add({
        endpoint, method, data,
        status: 'pending',
        queued_at: new Date().toISOString()
      });
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getPendingRequests() {
    const database = await openDB();
    return new Promise((resolve, reject) => {
      const tx = database.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).index('status').getAll('pending');
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function markDone(id) {
    const database = await openDB();
    return new Promise((resolve, reject) => {
      const tx = database.transaction(STORE_NAME, 'readwrite');
      const req = tx.objectStore(STORE_NAME).get(id);
      req.onsuccess = () => {
        const record = req.result;
        if (record) {
          record.status = 'synced';
          tx.objectStore(STORE_NAME).put(record);
        }
      };
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  // ── Offline Banner ───────────────────────────────────────────────
  function showOfflineBanner() {
    let banner = document.getElementById('offline-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'offline-banner';
      banner.setAttribute('role', 'alert');
      banner.setAttribute('aria-live', 'polite');
      banner.innerHTML = `
        <span>📶 You are offline — data will sync when reconnected</span>
        <button onclick="document.getElementById('offline-banner').style.display='none'" 
                aria-label="Dismiss offline notification">✕</button>
      `;
      banner.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; z-index: 99999;
        background: #c0392b; color: white; padding: 10px 20px;
        display: flex; align-items: center; justify-content: space-between;
        font-family: Poppins, sans-serif; font-size: 0.9rem; font-weight: 600;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
      `;
      banner.querySelector('button').style.cssText = `
        background: none; border: none; color: white; cursor: pointer;
        font-size: 1.1rem; padding: 0 8px;
      `;
      document.body.prepend(banner);
    }
    banner.style.display = 'flex';
  }

  function hideOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.style.display = 'none';
  }

  // ── Sync Queue on Reconnect ──────────────────────────────────────
  async function syncQueue() {
    const pending = await getPendingRequests();
    if (pending.length === 0) return;
    
    console.log(\`[OfflineSync] Replaying \${pending.length} queued requests...\`);
    
    for (const item of pending) {
      try {
        const options = {
          method: item.method,
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' }
        };
        if (item.data && item.method !== 'GET') {
          options.body = JSON.stringify(item.data);
        }
        const response = await fetch(item.endpoint, options);
        if (response.ok) {
          await markDone(item.id);
          console.log(\`[OfflineSync] ✅ Synced: \${item.endpoint}\`);
        }
      } catch (e) {
        console.warn(\`[OfflineSync] Failed to sync \${item.endpoint}:\`, e);
      }
    }
    
    // Show success toast if available
    if (window.Toast && window.Toast.show) {
      window.Toast.show('✅ Offline data synced successfully!', 'success');
    }
  }

  // ── Network Status Listeners ─────────────────────────────────────
  window.addEventListener('online', () => {
    hideOfflineBanner();
    syncQueue();
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.ready.then(reg => {
        if (reg.sync) reg.sync.register('sync-forms').catch(() => syncQueue());
        else syncQueue();
      });
    }
  });

  window.addEventListener('offline', showOfflineBanner);

  // ── Service Worker Message Handler ───────────────────────────────
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'REPLAY_QUEUE') {
        syncQueue();
      }
    });
  }

  // ── Check initial state ──────────────────────────────────────────
  if (!navigator.onLine) showOfflineBanner();

  // ── Public API ───────────────────────────────────────────────────
  window.OfflineSync = { queueRequest, syncQueue, getPendingRequests };

})();
