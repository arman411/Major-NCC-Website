/**
 * admin-onboarding.js — Step-by-step ANO onboarding wizard
 * Upgrade 3: Guides the ANO through the dashboard on first login
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'ncc_admin_onboarding_done_v1';

  const steps = [
    {
      target: null, // Full-screen intro step
      title: '👋 Welcome to NCC Portal!',
      content: 'This is your admin dashboard for managing cadets, notices, attendance, and more. This quick tour will show you the key features in under 2 minutes.',
      position: 'center'
    },
    {
      target: '[data-tour="quick-actions"]',
      title: '⚡ Quick Actions',
      content: 'Use these large buttons for the most common tasks — marking attendance, posting notices, viewing cadets, and downloading reports.',
      position: 'bottom'
    },
    {
      target: '[data-tour="cadets-section"]',
      title: '👥 Manage Cadets',
      content: 'View all enrolled cadets here. You can approve, reject, or view individual profiles. New enrollments appear at the top.',
      position: 'bottom'
    },
    {
      target: '[data-tour="notices-section"]',
      title: '📢 Post Notices',
      content: 'Create notices for upcoming camps, inspections, and events. Notices appear on the public portal immediately.',
      position: 'bottom'
    },
    {
      target: '[data-tour="backup-btn"]',
      title: '💾 Backup Your Data',
      content: 'Regularly download a backup of the database using this button. Store it safely — it contains all cadet records.',
      position: 'top'
    }
  ];

  let currentStep = 0;
  let overlay = null;
  let spotlight = null;
  let tooltip = null;

  function shouldShowOnboarding() {
    return !localStorage.getItem(STORAGE_KEY);
  }

  function createOnboardingUI() {
    // Overlay
    overlay = document.createElement('div');
    overlay.id = 'onboarding-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Admin Onboarding Tour');
    overlay.style.cssText = `
      position: fixed; inset: 0; z-index: 99990;
      background: rgba(0,0,0,0.65); backdrop-filter: blur(3px);
      transition: opacity 0.3s;
    `;

    // Tooltip card
    tooltip = document.createElement('div');
    tooltip.id = 'onboarding-tooltip';
    tooltip.style.cssText = `
      position: fixed; z-index: 99999;
      background: white; border-radius: 16px;
      padding: 28px 32px; max-width: 380px; width: 90vw;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      font-family: Poppins, sans-serif;
      transition: all 0.3s ease;
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(tooltip);

    // Close on overlay click
    overlay.addEventListener('click', finishOnboarding);
  }

  function showStep(index) {
    const step = steps[index];
    if (!step) { finishOnboarding(); return; }

    // Position tooltip
    let top = '50%', left = '50%', transform = 'translate(-50%, -50%)';
    
    if (step.target && step.position !== 'center') {
      const el = document.querySelector(step.target);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => positionNearElement(el, step.position), 300);
      }
    }

    tooltip.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <span style="font-size:0.75rem;font-weight:700;color:#3498db;text-transform:uppercase;letter-spacing:1px;">
          Step \${index + 1} of \${steps.length}
        </span>
        <button id="onboarding-skip" style="background:none;border:none;cursor:pointer;color:#999;font-size:0.8rem;font-family:Poppins,sans-serif;"
                aria-label="Skip tour">Skip Tour ✕</button>
      </div>
      <h3 style="font-size:1.15rem;font-weight:800;color:#0d2b5e;margin-bottom:10px;">\${step.title}</h3>
      <p style="font-size:0.9rem;color:#555;line-height:1.6;margin-bottom:24px;">\${step.content}</p>
      <div style="display:flex;gap:10px;justify-content:flex-end;">
        \${index > 0 ? '<button id="onboarding-prev" style="background:#f5f5f5;border:none;cursor:pointer;padding:10px 20px;border-radius:8px;font-family:Poppins,sans-serif;font-weight:600;color:#555;" aria-label="Previous step">← Back</button>' : ''}
        <button id="onboarding-next" style="background:linear-gradient(135deg,#0d2b5e,#1a4a9e);border:none;cursor:pointer;padding:10px 24px;border-radius:8px;font-family:Poppins,sans-serif;font-weight:700;color:white;" aria-label="\${index === steps.length - 1 ? 'Finish tour' : 'Next step'}">
          \${index === steps.length - 1 ? '🎉 Got it!' : 'Next →'}
        </button>
      </div>
    `;

    if (step.position === 'center' || !step.target) {
      tooltip.style.top = '50%';
      tooltip.style.left = '50%';
      tooltip.style.transform = 'translate(-50%, -50%)';
    }

    // Event listeners
    document.getElementById('onboarding-next').onclick = () => {
      currentStep++;
      showStep(currentStep);
    };
    const prevBtn = document.getElementById('onboarding-prev');
    if (prevBtn) prevBtn.onclick = () => { currentStep--; showStep(currentStep); };
    document.getElementById('onboarding-skip').onclick = finishOnboarding;
  }

  function positionNearElement(el, position) {
    const rect = el.getBoundingClientRect();
    const tipH = tooltip.offsetHeight;
    const tipW = tooltip.offsetWidth;
    
    if (position === 'bottom') {
      tooltip.style.top = \`\${rect.bottom + 16 + window.scrollY}px\`;
      tooltip.style.left = \`\${rect.left + rect.width / 2 - tipW / 2}px\`;
      tooltip.style.transform = 'none';
    } else if (position === 'top') {
      tooltip.style.top = \`\${rect.top - tipH - 16 + window.scrollY}px\`;
      tooltip.style.left = \`\${rect.left + rect.width / 2 - tipW / 2}px\`;
      tooltip.style.transform = 'none';
    }
  }

  function finishOnboarding() {
    localStorage.setItem(STORAGE_KEY, 'true');
    if (overlay) { overlay.remove(); overlay = null; }
    if (tooltip) { tooltip.remove(); tooltip = null; }
  }

  function startOnboarding() {
    createOnboardingUI();
    showStep(0);
  }

  // Public API
  window.AdminOnboarding = { start: startOnboarding, reset: () => localStorage.removeItem(STORAGE_KEY) };

  // Auto-start on admin dashboard pages
  document.addEventListener('DOMContentLoaded', () => {
    const isAdminPage = document.body.classList.contains('admin-page') ||
                        document.getElementById('admin-dashboard') ||
                        document.querySelector('[data-tour]');
    if (isAdminPage && shouldShowOnboarding()) {
      setTimeout(startOnboarding, 1500); // Delay to let page settle
    }
  });

})();
