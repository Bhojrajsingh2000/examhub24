// timer.js — countdown timer for the mock test attempt page.
// Depends on window.EXAMHUB.remainingSeconds being set, and a #timer-box element.
// Calls window.onExamTimerExpired() (defined in exam.js) when time runs out.

(function () {
    let remaining = window.EXAMHUB.remainingSeconds;
    const timerBox = document.getElementById('timer-box');

    function format(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        const pad = (n) => String(n).padStart(2, '0');
        return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
    }

    function tick() {
        if (remaining <= 0) {
            timerBox.textContent = '00:00';
            clearInterval(intervalId);
            if (typeof window.onExamTimerExpired === 'function') {
                window.onExamTimerExpired();
            }
            return;
        }
        timerBox.textContent = format(remaining);
        remaining -= 1;
    }

    tick();
    const intervalId = setInterval(tick, 1000);
})();
