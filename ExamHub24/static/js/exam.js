// exam.js — drives the test-attempt page: question navigation, palette status,
// AJAX answer-saving (with a "Saving.../Saved" indicator), and submit (manual +
// auto on timer expiry), with double-submit and double-confirmation-dialog protection.

(function () {
    const blocks = Array.from(document.querySelectorAll('.q-block'));
    const paletteButtons = Array.from(document.querySelectorAll('.q-nav-btn'));
    const saveStatus = document.getElementById('save-status');
    let currentIndex = 0;
    let isSubmitting = false; // guards against the double "leave site?" dialog and double-submit
    const status = {}; // index -> 'answered' | 'marked' | 'not-answered' | 'not-visited'

    blocks.forEach((b, i) => { status[i] = 'not-visited'; });
    status[0] = 'not-answered';
    updatePalette();

    function getSelectedOption(index) {
        const block = blocks[index];
        const checked = block.querySelector('.option-input:checked');
        return checked ? checked.value : null;
    }

    function updatePalette() {
        paletteButtons.forEach((btn, i) => {
            btn.classList.remove('answered', 'marked', 'not-answered', 'not-visited', 'current');
            btn.classList.add(status[i]);
            if (i === currentIndex) btn.classList.add('current');
        });
    }

    function showQuestion(index) {
        blocks[currentIndex].classList.remove('active');
        blocks[index].classList.add('active');
        currentIndex = index;
        if (status[index] === 'not-visited') status[index] = 'not-answered';
        updatePalette();
    }

    function saveCurrentAnswer(markOnly) {
        const block = blocks[currentIndex];
        const qid = block.dataset.qid;
        const selected = getSelectedOption(currentIndex);

        if (markOnly) {
            status[currentIndex] = 'marked';
        } else {
            status[currentIndex] = selected ? 'answered' : 'not-answered';
        }

        if (saveStatus) saveStatus.textContent = 'Saving...';

        fetch(window.EXAMHUB.saveAnswerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.EXAMHUB.csrfToken,
            },
            body: JSON.stringify({ question_id: qid, selected_option: selected }),
        }).then((res) => {
            if (saveStatus) saveStatus.textContent = res.ok ? 'Saved' : 'Could not save — will retry on next action';
        }).catch(() => {
            if (saveStatus) saveStatus.textContent = 'Could not save — check your connection';
        });
    }

    document.getElementById('save-next-btn').addEventListener('click', function () {
        saveCurrentAnswer(false);
        if (currentIndex < blocks.length - 1) showQuestion(currentIndex + 1);
    });

    document.getElementById('mark-btn').addEventListener('click', function () {
        saveCurrentAnswer(true);
        if (currentIndex < blocks.length - 1) showQuestion(currentIndex + 1);
    });

    document.getElementById('prev-btn').addEventListener('click', function () {
        if (currentIndex > 0) showQuestion(currentIndex - 1);
    });

    document.getElementById('clear-btn').addEventListener('click', function () {
        const block = blocks[currentIndex];
        block.querySelectorAll('.option-input').forEach((el) => { el.checked = false; });
        status[currentIndex] = 'not-answered';
        updatePalette();
        saveCurrentAnswer(false);
    });

    paletteButtons.forEach((btn) => {
        btn.addEventListener('click', function () {
            saveCurrentAnswer(false);
            showQuestion(parseInt(btn.dataset.index, 10));
        });
    });

    function doSubmit(auto) {
        isSubmitting = true; // must be set BEFORE form.submit() so beforeunload doesn't double-prompt
        const submitBtn = document.getElementById('submit-btn');
        submitBtn.disabled = true; // prevent double-click submitting the form twice
        submitBtn.textContent = auto ? 'Time up — submitting...' : 'Submitting...';
        if (auto) document.getElementById('auto-flag').value = '1';
        document.getElementById('submit-form').submit();
    }

    document.getElementById('submit-btn').addEventListener('click', function (e) {
        e.preventDefault(); // we control submission manually so it only happens once, after confirmation
        if (isSubmitting) return;
        if (!confirm('Are you sure you want to submit the test? This cannot be undone.')) return;
        saveCurrentAnswer(false);
        doSubmit(false);
    });

    // Auto-submit when the timer (timer.js) reaches zero.
    window.onExamTimerExpired = function () {
        if (isSubmitting) return;
        saveCurrentAnswer(false);
        doSubmit(true);
    };

    // Warn on accidental tab close / reload during the test — but NOT during a real
    // submit, otherwise the browser's native dialog stacks on top of our own confirm().
    window.addEventListener('beforeunload', function (e) {
        if (isSubmitting) return;
        e.preventDefault();
        e.returnValue = '';
    });
})();
