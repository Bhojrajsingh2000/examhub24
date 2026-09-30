// ExamHub24 — global site scripts
document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 4 seconds
    document.querySelectorAll('.alert').forEach(function (alertEl) {
        setTimeout(function () {
            var alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            alert.close();
        }, 4000);
    });

    // --- Dark mode toggle -------------------------------------------------
    // Uses Bootstrap 5.3's built-in color-mode support (data-bs-theme on <html>).
    // The actual "apply on load" logic lives in an inline <script> in base.html's
    // <head> (runs before first paint, avoiding a light-mode flash) — this just
    // wires up the toggle button and keeps the icon in sync.
    var THEME_KEY = 'examhub24-theme';
    var htmlEl = document.documentElement;
    var toggleBtn = document.getElementById('theme-toggle-btn');
    var toggleIcon = document.getElementById('theme-toggle-icon');

    function updateIcon() {
        var isDark = htmlEl.getAttribute('data-bs-theme') === 'dark';
        if (toggleIcon) {
            toggleIcon.classList.toggle('bi-moon-stars', !isDark);
            toggleIcon.classList.toggle('bi-sun', isDark);
        }
    }
    updateIcon();

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            var isDark = htmlEl.getAttribute('data-bs-theme') === 'dark';
            var next = isDark ? 'light' : 'dark';
            htmlEl.setAttribute('data-bs-theme', next);
            localStorage.setItem(THEME_KEY, next);
            updateIcon();
        });
    }
});
