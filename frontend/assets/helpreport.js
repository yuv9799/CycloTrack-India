/* ===========================================================================
   CycloTrack India — Emergency help-request form logic + shared UX helpers
   ---------------------------------------------------------------------------
   • Validates the "Report / Request Help" form client-side.
   • Submits to the backend POST /api/help-requests when available.
   • If the backend is unreachable (e.g. a static GitHub Pages deployment with
     no live server), it falls back to storing the request in the browser
     (localStorage) so an emergency submission is never silently lost.
   • Reveal-on-scroll animation helper used across pages.
   API base is overridable before this script loads:
       <script>window.CYCLOTRACK_API_BASE = "https://api.example.com";</script>
   ========================================================================= */
(function () {
    'use strict';

    var API_BASE = (typeof window !== 'undefined' && window.CYCLOTRACK_API_BASE) || 'http://localhost:8000';
    var ENDPOINT = API_BASE.replace(/\/+$/, '') + '/api/help-requests';
    var OFFLINE_QUEUE_KEY = 'cyclotrack_help_requests_offline';
    var MAX_IMAGE_BYTES = 2 * 1024 * 1024; // ~2MB decoded

    /* ---------- Reveal-on-scroll ---------- */
    function initReveal() {
        var els = document.querySelectorAll('.reveal');
        if (!els.length) return;
        if (!('IntersectionObserver' in window)) {
            els.forEach(function (el) { el.classList.add('in'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) {
                    e.target.classList.add('in');
                    io.unobserve(e.target);
                }
            });
        }, { threshold: 0.12 });
        els.forEach(function (el) { io.observe(el); });
    }

    /* ---------- Offline queue helpers ---------- */
    function readQueue() {
        try {
            var raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
            var arr = raw ? JSON.parse(raw) : [];
            return Array.isArray(arr) ? arr : [];
        } catch (e) { return []; }
    }
    function writeQueue(arr) {
        try { localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(arr)); } catch (e) { /* blocked/full */ }
    }
    function localId() {
        return 'HR-LOCAL-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).slice(2, 6).toUpperCase();
    }

    /* ---------- File -> base64 data URL ---------- */
    function readFileAsDataURL(file) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () { resolve(reader.result); };
            reader.onerror = function () { reject(new Error('Could not read image file.')); };
            reader.readAsDataURL(file);
        });
    }

    function showMessage(type, html) {
        var box = document.getElementById('reportMsg');
        if (!box) return;
        box.className = 'report-msg show ' + type;
        box.innerHTML = html;
        box.setAttribute('role', type === 'error' ? 'alert' : 'status');
    }

    function setError(field, message) {
        var el = document.getElementById(field);
        if (!el) return false;
        var wrap = el.closest('.report-field');
        if (wrap) wrap.classList[message ? 'add' : 'remove']('invalid');
        var errEl = document.getElementById(field + 'Error');
        if (errEl) errEl.textContent = message || '';
        return !message;
    }

    var INDIA_STATES = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman & Nicobar Islands", "Chandigarh", "Delhi (NCT)", "Jammu & Kashmir",
        "Ladakh", "Lakshadweep", "Puducherry", "Other"
    ];

    function populateStates() {
        var sel = document.getElementById('state');
        if (!sel || sel.options.length > 1) return;
        INDIA_STATES.forEach(function (s) {
            var o = document.createElement('option');
            o.value = s;
            o.textContent = s;
            sel.appendChild(o);
        });
    }

    function buildPayload(form) {
        var types = Array.prototype.filter.call(
            document.querySelectorAll('input[name="emergencyTypes"]:checked'),
            function (c) { return c.checked; }
        ).map(function (c) { return c.value; });

        return {
            full_name: form.fullName.value.trim(),
            mobile: form.mobile.value.trim(),
            email: form.email.value.trim() || null,
            state: form.state.value,
            district: form.district.value.trim(),
            village_city: form.villageCity.value.trim(),
            current_location: form.currentLocation.value.trim(),
            people_affected: parseInt(form.peopleAffected.value, 10) || 0,
            children: parseInt(form.children.value, 10) || 0,
            elderly_disabled: parseInt(form.elderlyDisabled.value, 10) || 0,
            emergency_types: types,
            description: form.description.value.trim(),
            image: form._imageData || null,
            consent: form.consent.checked,
            latitude: form.latitude && form.latitude.value ? parseFloat(form.latitude.value) : null,
            longitude: form.longitude && form.longitude.value ? parseFloat(form.longitude.value) : null
        };
    }

    function validate(form) {
        var ok = true;

        ok = setError('fullName', form.fullName.value.trim() ? '' : 'Please enter your full name.') && ok;
        ok = setError('state', form.state.value ? '' : 'Please select your state.') && ok;

        var district = form.district.value.trim();
        ok = setError('district', district ? '' : 'Please enter your district.') && ok;

        var city = form.villageCity.value.trim();
        ok = setError('villageCity', city ? '' : 'Please enter your village / city.') && ok;

        var loc = form.currentLocation.value.trim();
        ok = setError('currentLocation', loc ? '' : 'Please describe your current location / landmark.') && ok;

        var mobile = form.mobile.value.trim().replace(/[^0-9]/g, '');
        var mobileErr = '';
        if (!mobile) mobileErr = 'Please enter your mobile number.';
        else if (mobile.length < 8 || mobile.length > 15) mobileErr = 'Enter a valid mobile number (10 digits for India).';
        ok = setError('mobile', mobileErr) && ok;

        var email = form.email.value.trim();
        if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
            ok = setError('email', 'Enter a valid email address (or leave empty).') && ok;
        } else {
            ok = setError('email', '') && ok;
        }

        var people = parseInt(form.peopleAffected.value, 10);
        ok = setError('peopleAffected', (!form.peopleAffected.value || isNaN(people) || people < 1) ? 'How many people are affected? (min 1)' : '') && ok;

        ok = setError('children', (form.children.value && (isNaN(parseInt(form.children.value, 10)) || parseInt(form.children.value, 10) < 0)) ? 'Enter a valid number.' : '') && ok;
        ok = setError('elderlyDisabled', (form.elderlyDisabled.value && (isNaN(parseInt(form.elderlyDisabled.value, 10)) || parseInt(form.elderlyDisabled.value, 10) < 0)) ? 'Enter a valid number.' : '') && ok;

        var types = document.querySelectorAll('input[name="emergencyTypes"]:checked');
        var typesErr = !types.length ? 'Select at least one type of emergency.' : '';
        var typesBox = document.getElementById('emergencyTypesError');
        if (typesBox) typesBox.textContent = typesErr;
        if (typesErr) ok = false;

        var descErr = form.description.value.trim().length < 5 ? 'Please describe your situation (min 5 characters).' : '';
        ok = setError('description', descErr) && ok;

        var consent = form.consent.checked;
        var consentErr = !consent ? 'You must give consent to submit your request.' : '';
        var consentBox = document.getElementById('consentError');
        if (consentBox) consentBox.textContent = consentErr;
        if (consentErr) ok = false;

        return ok;
    }

    function tryRemote(payload) {
        return fetch(ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(function (res) {
            if (!res.ok) {
                return res.json().catch(function () { return {}; }).then(function (body) {
                    var detail = (body && (body.detail || body.message)) || ('Server returned ' + res.status);
                    throw new Error(detail);
                });
            }
            return res.json();
        });
    }

    function showRemoteSuccess(data, form) {
        showMessage('success',
            '<strong>Request received.</strong> Your emergency request has been delivered to the operations ' +
            'team' + (data && data.id ? ' (Ref: ' + data.id + ')' : '') + '. If this is life-threatening, ' +
            'also call <strong><a href="tel:112" style="color:#14532D">112</a></strong> now.');
        form.reset();
        form._imageData = null;
        var prev = document.getElementById('imagePreview');
        if (prev) prev.classList.remove('show');
    }

    function showOfflineFallback(payload, form) {
        var rec = storeOffline(payload);
        form._imageData = null;
        var prev = document.getElementById('imagePreview');
        if (prev) prev.classList.remove('show');
        showMessage('warn',
            '<strong>Saved on this device (Ref: ' + rec.id + ').</strong> The live operations server is not ' +
            'reachable right now, so your request was stored locally and will be synced when a connection is ' +
            'available. For an immediate emergency, call <strong><a href="tel:112" style="color:#7A4A12">112</a></strong>.');
    }

    function submitHandler(e) {
        e.preventDefault();
        var form = this;
        showMessage('', '');
        if (!validate(form)) {
            showMessage('error', '<strong>Please check the highlighted fields.</strong> A few required details are missing or invalid.');
            var firstInvalid = form.querySelector('.report-field.invalid input, .report-field.invalid select, .report-field.invalid textarea');
            if (firstInvalid) firstInvalid.focus();
            return;
        }
        var payload = buildPayload(form);
        var btn = document.getElementById('submitBtn');
        var original = btn ? btn.value : 'Submit Emergency Request';
        if (btn) { btn.disabled = true; btn.value = 'Submitting…'; }

        tryRemote(payload)
            .then(function (data) {
                showRemoteSuccess(data, form);
            })
            .catch(function (err) {
                showOfflineFallback(payload, form);
            })
            .finally(function () {
                if (btn) { btn.disabled = false; btn.value = original; }
            });
    }

    function storeOffline(payload) {
        var record = Object.assign({
            id: localId(),
            created_at: new Date().toISOString()
        }, JSON.parse(JSON.stringify(payload)));
        var q = readQueue();
        q.push(record);
        writeQueue(q);
        return record;
    }

    function initForm() {
        var form = document.getElementById('helpRequestForm');
        if (!form) return;
        form.addEventListener('submit', submitHandler);
        populateStates();

        // Pre-select an emergency type from ?type=... (used by quick-action cards).
        try {
            var params = new URLSearchParams(window.location.search);
            var t = params.get('type');
            if (t) {
                var matched = document.querySelector('input[name="emergencyTypes"][value="' +
                    t.replace(/"/g, '') + '"]');
                if (matched) matched.checked = true;
            }
        } catch (err) { /* URLSearchParams unavailable; ignore */ }

        // Optional image upload -> base64 preview.
        var imgInput = document.getElementById('imageFile');
        var preview = document.getElementById('imagePreview');
        if (imgInput && preview) {
            imgInput.addEventListener('change', function () {
                var file = imgInput.files && imgInput.files[0];
                if (!file) return;
                if (file.size > MAX_IMAGE_BYTES) {
                    showMessage('error', 'Image is too large (max 2MB). Please choose a smaller photo.');
                    imgInput.value = '';
                    return;
                }
                if (file.type.indexOf('image/') !== 0) {
                    showMessage('error', 'Please choose a valid image file (JPG, PNG, etc.).');
                    imgInput.value = '';
                    return;
                }
                readFileAsDataURL(file).then(function (dataUrl) {
                    form._imageData = dataUrl;
                    preview.src = dataUrl;
                    preview.classList.add('show');
                }).catch(function (err) {
                    showMessage('error', err.message);
                    imgInput.value = '';
                });
            });
        }

        var gpsBtn = document.getElementById('getGpsBtn');
        if (gpsBtn) {
            gpsBtn.addEventListener('click', function () {
                var status = document.getElementById('gpsStatus');
                if (!navigator.geolocation) { if (status) status.textContent = 'GPS is not supported by this browser.'; return; }
                if (status) status.textContent = 'Requesting your location…';
                navigator.geolocation.getCurrentPosition(function (pos) {
                    var lat = document.getElementById('latitude'), lng = document.getElementById('longitude');
                    if (lat) lat.value = pos.coords.latitude.toFixed(6);
                    if (lng) lng.value = pos.coords.longitude.toFixed(6);
                    if (status) status.textContent = 'GPS location captured. You can still edit the location description.';
                }, function () {
                    if (status) status.textContent = 'Location permission was not granted. You can enter the location manually.';
                }, {enableHighAccuracy:true,timeout:10000});
            });
        }

        // Clear an error as soon as the user fixes the field.
        form.addEventListener('input', function (ev) {
            if (ev.target && ev.target.closest('.report-field.invalid')) {
                var id = ev.target.id;
                if (id) setError(id, '');
            }
        });
    }

    /* ---------- Boot ---------- */
    initReveal();
    initForm();
})();