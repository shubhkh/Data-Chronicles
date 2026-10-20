(function () {
    'use strict';

    const CIRCUMFERENCE = 2 * Math.PI * 118;

    const displayM = document.getElementById('pm-minutes');
    const displayS = document.getElementById('pm-seconds');
    const status = document.getElementById('pm-status');
    const ring = document.getElementById('pm-ring');
    const dotsWrap = document.getElementById('pm-dots');
    const taskInput = document.getElementById('pm-task');
    const startBtn = document.getElementById('pm-start-btn');
    const skipBtn = document.getElementById('pm-skip-btn');
    const resetBtn = document.getElementById('pm-reset-btn');
    const settingsWrap = document.querySelector('.pomo-settings');
    const setFocus = document.getElementById('pm-set-focus');
    const setShort = document.getElementById('pm-set-short');
    const setLong = document.getElementById('pm-set-long');
    const setRounds = document.getElementById('pm-set-rounds');
    const tabs = {
        focus: document.getElementById('pm-tab-focus'),
        short: document.getElementById('pm-tab-short'),
        long: document.getElementById('pm-tab-long'),
    };

    const MODE_ACCENT = { focus: 'rose', short: 'teal', long: 'blue' };
    const MODE_LABELS = { short: 'Short break', long: 'Long break' };
    const MODE_SETTING = { focus: setFocus, short: setShort, long: setLong };

    let mode = 'focus';
    let totalMs = 0;
    let remainingMs = 0;
    let endStamp = 0;
    let rafId = null;
    let completedSessions = 0;
    let audioCtx = null;

    const pad = (n) => String(n).padStart(2, '0');
    const clamp = (input, max) => {
        const v = Math.max(1, Math.min(max, parseInt(input.value, 10) || 1));
        input.value = v;
        return v;
    };

    function durations() {
        return {
            focus: clamp(setFocus, 120) * 60000,
            short: clamp(setShort, 60) * 60000,
            long: clamp(setLong, 60) * 60000,
        };
    }

    function rounds() {
        return clamp(setRounds, 12);
    }

    function modeLabel() {
        return mode === 'focus'
            ? `#${completedSessions + 1} · Time to focus!`
            : MODE_LABELS[mode];
    }

    function render() {
        const totalSec = Math.ceil(remainingMs / 1000);
        displayM.textContent = pad(Math.floor(totalSec / 60));
        displayS.textContent = pad(totalSec % 60);
        const fraction = totalMs > 0 ? remainingMs / totalMs : 0;
        ring.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - fraction));
        document.title = rafId !== null
            ? `${pad(Math.floor(totalSec / 60))}:${pad(totalSec % 60)} · ${mode === 'focus' ? 'Focus' : 'Break'}`
            : 'Pomodoro — Productivity Timer';
    }

    function renderDots() {
        dotsWrap.innerHTML = '';
        for (let i = 0; i < rounds(); i++) {
            const dot = document.createElement('span');
            dot.className = 'dot' + (i < completedSessions ? ' done' : '');
            dotsWrap.appendChild(dot);
        }
    }

    function setMode(next) {
        mode = next;
        totalMs = durations()[mode];
        remainingMs = totalMs;
        document.body.dataset.accent = MODE_ACCENT[mode];
        status.textContent = modeLabel();
        status.classList.remove('finished');
        Object.entries(tabs).forEach(([key, tab]) =>
            tab.classList.toggle('active', key === mode)
        );
        render();
    }

    function beep() {
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.25, 0.5].forEach((delay) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.frequency.value = mode === 'focus' ? 660 : 880;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.001, audioCtx.currentTime + delay);
                gain.gain.exponentialRampToValueAtTime(0.4, audioCtx.currentTime + delay + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + delay + 0.2);
                osc.connect(gain).connect(audioCtx.destination);
                osc.start(audioCtx.currentTime + delay);
                osc.stop(audioCtx.currentTime + delay + 0.22);
            });
        } catch (e) { /* audio unavailable */ }
    }

    function nextMode() {
        if (mode === 'focus') {
            completedSessions += 1;
            renderDots();
            return completedSessions >= rounds() ? 'long' : 'short';
        }
        if (mode === 'long') completedSessions = 0;
        renderDots();
        return 'focus';
    }

    const LOG_KIND = { focus: 'pomodoro_focus', short: 'short_break', long: 'long_break' };

    function finishPhase() {
        beep();
        window.logSession(LOG_KIND[mode], totalMs / 1000, mode === 'focus' ? taskInput.value : '');
        setMode(nextMode());
        endStamp = performance.now() + remainingMs;
        rafId = requestAnimationFrame(tick);
    }

    function tick() {
        remainingMs = Math.max(0, endStamp - performance.now());
        render();
        if (remainingMs <= 0) {
            finishPhase();
            return;
        }
        rafId = requestAnimationFrame(tick);
    }

    function startPause() {
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
            startBtn.textContent = 'Resume';
            status.textContent = 'Paused';
            return;
        }
        status.classList.remove('finished');
        status.textContent = modeLabel();
        startBtn.textContent = 'Pause';
        settingsWrap.classList.add('locked');
        endStamp = performance.now() + remainingMs;
        rafId = requestAnimationFrame(tick);
    }

    function skip() {
        cancelAnimationFrame(rafId);
        rafId = null;
        setMode(nextMode());
        startBtn.textContent = 'Start';
        settingsWrap.classList.remove('locked');
    }

    function reset() {
        cancelAnimationFrame(rafId);
        rafId = null;
        completedSessions = 0;
        renderDots();
        setMode('focus');
        startBtn.textContent = 'Start';
        settingsWrap.classList.remove('locked');
    }

    function addMinutes(n) {
        const runningOrPaused = rafId !== null || remainingMs !== totalMs;
        if (runningOrPaused) {
            remainingMs += n * 60000;
            totalMs += n * 60000;
            if (rafId !== null) endStamp += n * 60000;
            render();
        } else {
            const input = MODE_SETTING[mode];
            input.value = parseInt(input.value, 10) + n;
            setMode(mode);
        }
    }

    Object.entries(tabs).forEach(([key, tab]) => {
        tab.addEventListener('click', () => {
            if (rafId === null) setMode(key);
        });
    });

    document.querySelectorAll('.chip[data-add]').forEach((chip) =>
        chip.addEventListener('click', () => addMinutes(parseInt(chip.dataset.add, 10)))
    );

    [setFocus, setShort, setLong].forEach((input) =>
        input.addEventListener('input', () => {
            if (rafId === null) setMode(mode);
        })
    );
    setRounds.addEventListener('input', () => {
        if (rafId === null) { completedSessions = 0; renderDots(); }
    });

    taskInput.value = localStorage.getItem('pm-task') || '';
    taskInput.addEventListener('input', () =>
        localStorage.setItem('pm-task', taskInput.value)
    );

    // Persist settings across visits
    try {
        const saved = JSON.parse(localStorage.getItem('pm-settings') || 'null');
        if (saved) {
            setFocus.value = saved.focus; setShort.value = saved.short;
            setLong.value = saved.long; setRounds.value = saved.rounds;
        }
    } catch (e) { /* ignore */ }
    function saveSettings() {
        localStorage.setItem('pm-settings', JSON.stringify({
            focus: setFocus.value, short: setShort.value,
            long: setLong.value, rounds: setRounds.value,
        }));
    }
    [setFocus, setShort, setLong, setRounds].forEach((input) =>
        input.addEventListener('input', saveSettings)
    );

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') { e.preventDefault(); startPause(); }
        if (e.code === 'KeyS' && rafId !== null) skip();
    });

    startBtn.addEventListener('click', startPause);
    skipBtn.addEventListener('click', skip);
    resetBtn.addEventListener('click', reset);

    renderDots();
    setMode('focus');
})();
