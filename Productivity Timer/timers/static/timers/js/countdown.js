(function () {
    'use strict';

    const CIRCUMFERENCE = 2 * Math.PI * 118;

    const displayH = document.getElementById('cd-hours');
    const displayM = document.getElementById('cd-minutes');
    const displayS = document.getElementById('cd-seconds');
    const status = document.getElementById('cd-status');
    const ring = document.getElementById('cd-ring');
    const inputsWrap = document.getElementById('cd-inputs');
    const inH = document.getElementById('cd-in-hours');
    const inM = document.getElementById('cd-in-minutes');
    const inS = document.getElementById('cd-in-seconds');
    const startBtn = document.getElementById('cd-start-btn');
    const resetBtn = document.getElementById('cd-reset-btn');

    let totalMs = 0;
    let remainingMs = 0;
    let endStamp = 0;
    let rafId = null;
    let audioCtx = null;

    const pad = (n) => String(n).padStart(2, '0');

    const clamp = (input, max) => {
        const v = Math.max(0, Math.min(max, parseInt(input.value, 10) || 0));
        input.value = v;
        return v;
    };

    function readInputs() {
        const h = clamp(inH, 99);
        const m = clamp(inM, 59);
        const s = clamp(inS, 59);
        return (h * 3600 + m * 60 + s) * 1000;
    }

    function render(ms) {
        const totalSec = Math.ceil(ms / 1000);
        displayH.textContent = pad(Math.floor(totalSec / 3600));
        displayM.textContent = pad(Math.floor((totalSec % 3600) / 60));
        displayS.textContent = pad(totalSec % 60);
        const fraction = totalMs > 0 ? ms / totalMs : 0;
        ring.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - fraction));
        document.title = ms > 0 && rafId !== null
            ? `${pad(Math.floor(totalSec / 3600))}:${pad(Math.floor((totalSec % 3600) / 60))}:${pad(totalSec % 60)} · Countdown`
            : 'Countdown — Productivity Timer';
    }

    function beep() {
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.25, 0.5].forEach((delay) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.frequency.value = 880;
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

    function finish() {
        cancelAnimationFrame(rafId);
        rafId = null;
        remainingMs = 0;
        render(0);
        status.textContent = "Time's up!";
        status.classList.add('finished');
        window.logSession('countdown', totalMs / 1000);
        startBtn.textContent = 'Start';
        inputsWrap.classList.remove('locked');
        beep();
    }

    function tick() {
        remainingMs = Math.max(0, endStamp - performance.now());
        render(remainingMs);
        if (remainingMs <= 0) {
            finish();
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
            inputsWrap.classList.remove('locked');
            return;
        }
        if (remainingMs <= 0) {
            totalMs = readInputs();
            remainingMs = totalMs;
            if (totalMs <= 0) return;
        }
        status.classList.remove('finished');
        status.textContent = 'Running';
        startBtn.textContent = 'Pause';
        resetBtn.disabled = false;
        inputsWrap.classList.add('locked');
        endStamp = performance.now() + remainingMs;
        rafId = requestAnimationFrame(tick);
    }

    function reset() {
        cancelAnimationFrame(rafId);
        rafId = null;
        totalMs = readInputs();
        remainingMs = totalMs;
        render(remainingMs);
        status.textContent = 'Ready';
        status.classList.remove('finished');
        startBtn.textContent = 'Start';
        resetBtn.disabled = true;
        inputsWrap.classList.remove('locked');
    }

    document.querySelectorAll('.chip[data-preset]').forEach((chip) => {
        chip.addEventListener('click', () => {
            const secs = parseInt(chip.dataset.preset, 10);
            inH.value = Math.floor(secs / 3600);
            inM.value = Math.floor((secs % 3600) / 60);
            inS.value = secs % 60;
            if (rafId === null) reset();
        });
    });

    [inH, inM, inS].forEach((input) =>
        input.addEventListener('input', () => { if (rafId === null) reset(); })
    );

    startBtn.addEventListener('click', startPause);
    resetBtn.addEventListener('click', reset);

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') { e.preventDefault(); startPause(); }
    });

    reset();
})();
