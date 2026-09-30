// ExamHub24 service worker — basic offline support.
//
// IMPORTANT: this file must be served from the SITE ROOT (/service-worker.js), not from
// /static/js/. A service worker's control scope is limited to its own directory and
// below — serving it from /static/ would mean it could only ever control /static/ URLs,
// not your actual pages. See core/views.py `service_worker_view` + core/urls.py for how
// that's done here (a plain Django view returning this file's content at the root URL).

const CACHE_NAME = 'examhub24-shell-v1';

// Precached on install — the bare minimum needed to show *something* offline instead of
// the browser's default "no internet" error page. Deliberately small: this is app-shell
// caching (works offline for previously-visited pages), not full offline test-taking —
// a mock test still needs a live connection to fetch questions and submit answers.
const PRECACHE_URLS = [
    '/offline/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/images/logo-icon.svg',
    '/static/manifest.json',
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(PRECACHE_URLS);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys.filter(function (key) { return key !== CACHE_NAME; })
                    .map(function (key) { return caches.delete(key); })
            );
        }).then(function () {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', function (event) {
    const request = event.request;

    // Only handle GET requests — never intercept POST (form submits, test answers,
    // payments) with cache logic; those must always go to the network.
    if (request.method !== 'GET') return;

    if (request.mode === 'navigate') {
        // Page navigations: try the network first (so content is always fresh when
        // online), fall back to the offline page only when the network truly fails.
        event.respondWith(
            fetch(request).catch(function () {
                return caches.match('/offline/');
            })
        );
        return;
    }

    // Static assets (CSS/JS/images): cache-first, since these rarely change and
    // WhiteNoise already serves them with far-future cache headers in production.
    if (request.url.includes('/static/')) {
        event.respondWith(
            caches.match(request).then(function (cached) {
                return cached || fetch(request).then(function (response) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) { cache.put(request, clone); });
                    return response;
                });
            })
        );
    }
    // Everything else (API-ish calls, AJAX save-answer, etc.) is left untouched and
    // goes straight to the network, since caching those would risk showing stale data.
});
