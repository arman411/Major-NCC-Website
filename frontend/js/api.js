/* ========================================================
   NCC WEBSITE - API Client
   Handles all fetch requests to the Flask REST backend.
   ======================================================== */

const API_BASE = window.location.origin + '/api';

/**
 * Helper strictly for making JSON requests
 */
async function fetchJson(endpoint, options = {}) {
    // Configure default headers for JSON
    const headers = {
        'Accept': 'application/json',
        ...options.headers
    };

    // If body is an object and not FormData, stringify it
    if (options.body && !(options.body instanceof FormData) && typeof options.body === 'object') {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
        credentials: 'same-origin' // Ensure cookies (sessions) are sent
    });

    // Check content-type to see if the response is actually JSON
    const contentType = res.headers.get('content-type');
    let data;
    if (contentType && contentType.includes('application/json')) {
        data = await res.json();
    } else {
        data = { success: res.ok, message: await res.text() };
    }
    
    // Attach status info for error handling
    if (!res.ok) {
        throw { status: res.status, data };
    }
    
    return data;
}

/**
 * Handle form submission generically, mapping it to an API endpoint
 */
function handleFormSubmit(formId, endpoint, method = 'POST', onSuccess = null) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Show loading state if any button exists
        const btn = form.querySelector('button[type="submit"]');
        let originalText = '';
        if (btn) {
            originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            btn.disabled = true;
        }

        // Gather form data
        const formData = new FormData(form);
        const hasFile = Array.from(formData.values()).some(val => val instanceof File && val.name !== '');

        let options = { method };
        if (hasFile) {
            options.body = formData; // Let browser set multipart/form-data
        } else {
            // Convert to JSON object for standard forms without files
            const obj = {};
            formData.forEach((value, key) => obj[key] = value);
            options.body = obj;
        }

        try {
            const result = await fetchJson(endpoint, options);
            if (result.success) {
                // Show success UI
                if (onSuccess) {
                    onSuccess(result);
                } else {
                    alert(result.message || 'Operation successful!');
                    form.reset();
                }
            } else {
                alert('Error: ' + (result.message || 'Action failed'));
            }
        } catch (err) {
            console.error('API Error:', err);
            const msg = err.data && err.data.message ? err.data.message : 'A network/server error occurred.';
            alert(msg);
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    });
}
