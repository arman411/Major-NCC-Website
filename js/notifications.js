/**
 * NCC Portal Notification Manager
 * Integrates real PWA Push Notifications and custom real-time polling fallback.
 */

const NOTIFICATION_POLL_INTERVAL = 10000; // 10 seconds
let notificationPollTimer = null;
let lastSeenAlertId = 0;

// Base64 helper for VAPID keys
function urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

const NCCNotification = {
  // Check if push & SW are supported
  isSupported() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  },

  // Initialize notifications
  async init() {
    console.log("[Notification System] Initializing...");
    
    if (typeof Notification === 'undefined') {
      console.warn("[Notification System] Notification object is undefined on this browser.");
      return;
    }
    
    // Check if permission is already granted
    if (Notification.permission === 'granted') {
      console.log("[Notification System] Notification permission is granted.");
      this.startPollingFallback(); // Start polling for simulation / history sync
      this.syncSubscription();      // Try to register/sync PWA Push subscription
    } else if (Notification.permission !== 'denied') {
      console.log("[Notification System] Notification permission is promptable.");
    }
  },

  // Request browser permissions
  async requestPermission() {
    if (!('Notification' in window)) {
      console.warn("This browser does not support desktop notifications.");
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        console.log("Notification permission granted!");
        
        // Try showing a test notification
        this.showLocalNotification("Notifications Enabled", "You will now receive real-time alerts for notices, camps, and achievements!");
        
        // Start polling fallback for dynamic simulation
        this.startPollingFallback();
        
        // Try real PWA Push Subscription
        await this.syncSubscription();
        return true;
      }
      return false;
    } catch (err) {
      console.error("Error requesting permission:", err);
      return false;
    }
  },

  // Try to register Web Push Subscription
  async syncSubscription() {
    if (!this.isSupported()) return;

    try {
      const registration = await navigator.serviceWorker.ready;
      
      // Fetch public VAPID key if we want real push (if backend outputs a key, or we can use a standard key)
      let vapidPublicKey = null;
      try {
        const keyRes = await fetch('/api/notifications/vapid-key');
        if (keyRes.ok) {
          const keyData = await keyRes.json();
          vapidPublicKey = keyData.publicKey;
        }
      } catch (e) {
        console.log("No dynamic VAPID key from backend, using simulation mode.");
      }

      if (!vapidPublicKey) {
        console.log("[PWA Push] VAPID keys not configured. Operating in simulated real-time mode.");
        return;
      }

      const convertedVapidKey = urlB64ToUint8Array(vapidPublicKey);

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedVapidKey
      });

      console.log("[PWA Push] Subscription successful:", subscription);

      // Send to backend
      const res = await fetch('/api/notifications/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(subscription)
      });

      const data = await res.json();
      if (!data.error) {
        console.log("[PWA Push] Subscription synchronized with backend.");
      } else {
        console.error("[PWA Push] Failed to sync subscription:", data.message);
      }
    } catch (err) {
      console.warn("[PWA Push] Could not subscribe to native push manager:", err);
      console.log("[PWA Push] Continuing in Simulated Real-Time Mode.");
    }
  },

  // Polling simulation for offline, localhost, or dev mode
  startPollingFallback() {
    if (notificationPollTimer) clearInterval(notificationPollTimer);

    // Initial fetch of recent alerts to set lastSeenAlertId without triggering duplicate alerts
    this.pollAlerts(true);

    notificationPollTimer = setInterval(() => {
      this.pollAlerts(false);
    }, NOTIFICATION_POLL_INTERVAL);
    
    console.log("[Notification System] Real-time fallback polling active.");
  },

  stopPolling() {
    if (notificationPollTimer) {
      clearInterval(notificationPollTimer);
      notificationPollTimer = null;
    }
  },

  // Fetch recent notifications from server
  async pollAlerts(isInitialLoad = false) {
    try {
      const res = await fetch('/api/notifications/poll');
      if (!res.ok) return;

      const data = await res.json();
      if (data.error || !data.alerts || data.alerts.length === 0) return;

      const latestAlerts = data.alerts;

      if (isInitialLoad) {
        // Just establish the starting point
        if (latestAlerts.length > 0) {
          lastSeenAlertId = latestAlerts[0].id;
        }
        return;
      }

      // We poll from oldest to newest of the unseen alerts
      const unseenAlerts = latestAlerts.filter(a => a.id > lastSeenAlertId).reverse();
      
      if (unseenAlerts.length > 0) {
        unseenAlerts.forEach(alert => {
          this.showLocalNotification(alert.message_body, alert.cadet_name || "ANO Office Update", alert.category || "info");
          
          // Trigger a custom UI notification event so active pages can update dashboards dynamically
          const event = new CustomEvent('ncc-new-alert', { detail: alert });
          window.dispatchEvent(event);
        });
        
        lastSeenAlertId = latestAlerts[0].id;
      }
    } catch (err) {
      console.warn("Polling alerts failed:", err);
    }
  },

  // Show a visual browser notification or toast
  showLocalNotification(body, title = "NCC Portal Update", category = "info") {
    // 1. If document is hidden, show system notification
    if (document.hidden && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then(reg => {
          reg.showNotification(title, {
            body: body,
            icon: '/images/logo.png',
            badge: '/images/logo.png',
            vibrate: [100, 50, 100],
            data: { url: '/pages/cadet-portal.html' }
          });
        });
      } else {
        new Notification(title, {
          body: body,
          icon: '/images/logo.png'
        });
      }
    } else {
      // 2. If tab is focused, play subtle priority chime and display premium priority Toast in-app!
      this.playMicroChime(category);
      this.showPremiumToast(title, body, category);
    }
  },

  // Premium UI Toast notification with dynamic category styling
  showPremiumToast(title, message, category = "info") {
    // Check if toast container exists
    let container = document.getElementById('premium-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'premium-toast-container';
      container.style.cssText = `
        position: fixed;
        top: 24px;
        right: 24px;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 12px;
        pointer-events: none;
      `;
      document.body.appendChild(container);
    }

    // Set styling and icons based on category
    let borderColor = '#f59e0b';
    let iconClass = 'fa-solid fa-bell';
    let labelColor = '#f59e0b';
    let badgeText = 'Update';

    if (category === 'danger') {
      borderColor = '#e74c3c';
      iconClass = 'fa-solid fa-triangle-exclamation';
      labelColor = '#e74c3c';
      badgeText = 'CRITICAL';
    } else if (category === 'warning') {
      borderColor = '#f39c12';
      iconClass = 'fa-solid fa-circle-exclamation';
      labelColor = '#f39c12';
      badgeText = 'WARNING';
    } else if (category === 'success') {
      borderColor = '#2ecc71';
      iconClass = 'fa-solid fa-circle-check';
      labelColor = '#2ecc71';
      badgeText = 'NOTICE';
    } else {
      borderColor = '#3498db';
      iconClass = 'fa-solid fa-circle-info';
      labelColor = '#3498db';
      badgeText = 'INFO';
    }

    const toast = document.createElement('div');
    toast.className = 'premium-toast';
    toast.style.cssText = `
      min-width: 320px;
      max-width: 400px;
      background: rgba(15, 23, 42, 0.95);
      border-left: 4px solid ${borderColor};
      color: #f8fafc;
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(10px);
      display: flex;
      flex-direction: column;
      gap: 4px;
      transform: translateX(120%);
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: auto;
      cursor: pointer;
    `;

    toast.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: 700; font-size: 0.95rem; color: ${labelColor}; display: flex; align-items: center; gap: 8px;">
          <i class="${iconClass} animate-bounce"></i> ${title} <span style="font-size:0.62rem;background:rgba(255,255,255,0.08);padding:1px 6px;border-radius:10px;color:#cbd5e1;font-weight:600;">${badgeText}</span>
        </span>
        <button style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 0.85rem;" onclick="event.stopPropagation(); this.parentElement.parentElement.remove()">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div style="font-size: 0.875rem; color: #cbd5e1; line-height: 1.4;">${message}</div>
    `;

    toast.onclick = () => {
      window.location.href = '/pages/cadet-portal.html';
    };

    container.appendChild(toast);

    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 50);

    // Auto remove after 7 seconds
    setTimeout(() => {
      if (toast && toast.parentElement) {
        toast.style.transform = 'translateX(120%)';
        toast.style.opacity = '0';
        setTimeout(() => { if (toast && toast.parentElement) toast.remove(); }, 400);
      }
    }, 7000);
  },

  // Advanced Audio alert synthesizer based on category
  playMicroChime(category = 'info') {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const gainNode = audioCtx.createGain();
      gainNode.connect(audioCtx.destination);

      if (category === 'danger') {
        // Low critical siren alarm sweep
        const osc = audioCtx.createOscillator();
        osc.connect(gainNode);
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, audioCtx.currentTime);
        osc.frequency.linearRampToValueAtTime(120, audioCtx.currentTime + 0.18);
        osc.frequency.linearRampToValueAtTime(220, audioCtx.currentTime + 0.36);
        
        gainNode.gain.setValueAtTime(0.06, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
        
        osc.start(audioCtx.currentTime);
        osc.stop(audioCtx.currentTime + 0.5);
      } else if (category === 'warning') {
        // High-pitched warning pulse chime (double bip)
        const osc = audioCtx.createOscillator();
        osc.connect(gainNode);
        osc.type = 'square';
        osc.frequency.setValueAtTime(920, audioCtx.currentTime);
        
        gainNode.gain.setValueAtTime(0.04, audioCtx.currentTime);
        gainNode.gain.setValueAtTime(0.001, audioCtx.currentTime + 0.08);
        gainNode.gain.setValueAtTime(0.04, audioCtx.currentTime + 0.12);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.28);
        
        osc.start(audioCtx.currentTime);
        osc.stop(audioCtx.currentTime + 0.28);
      } else if (category === 'success') {
        // Full Ascending major chord sweep (C5 -> E5 -> G5 -> C6)
        const notes = [523.25, 659.25, 783.99, 1046.50];
        notes.forEach((freq, idx) => {
          const osc = audioCtx.createOscillator();
          const noteGain = audioCtx.createGain();
          osc.connect(noteGain);
          noteGain.connect(gainNode);
          
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, audioCtx.currentTime + (idx * 0.06));
          
          noteGain.gain.setValueAtTime(0.03, audioCtx.currentTime + (idx * 0.06));
          noteGain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (idx * 0.06) + 0.35);
          
          osc.start(audioCtx.currentTime + (idx * 0.06));
          osc.stop(audioCtx.currentTime + (idx * 0.06) + 0.35);
        });
        
        gainNode.gain.setValueAtTime(1.0, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.6);
      } else {
        // Info (default): Ascent pleasant chime sweep
        const osc1 = audioCtx.createOscillator();
        const osc2 = audioCtx.createOscillator();
        
        osc1.connect(gainNode);
        osc2.connect(gainNode);
        
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5
        osc1.frequency.exponentialRampToValueAtTime(880.00, audioCtx.currentTime + 0.15); // A5
        
        osc2.type = 'triangle';
        osc2.frequency.setValueAtTime(659.25, audioCtx.currentTime); // E5
        osc2.frequency.exponentialRampToValueAtTime(1046.50, audioCtx.currentTime + 0.15); // C6
        
        gainNode.gain.setValueAtTime(0.06, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
        
        osc1.start(audioCtx.currentTime);
        osc2.start(audioCtx.currentTime);
        osc1.stop(audioCtx.currentTime + 0.4);
        osc2.stop(audioCtx.currentTime + 0.4);
      }
    } catch (e) {
      console.log("Audio alert playback ignored by browser autoplay restriction.");
    }
  }
};

// Auto-run initialization when loaded
document.addEventListener('DOMContentLoaded', () => {
  NCCNotification.init();
});
