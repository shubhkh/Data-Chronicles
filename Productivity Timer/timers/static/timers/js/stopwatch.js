(function () {
    'use strict';

    const displayMin = document.getElementById('sw-minutes');
    const displaySec = document.getElementById('sw-seconds');
    const displayCenti = document.getElementById('sw-centiseconds');
    const startBtn = document.getElementById('sw-start-btn');
    const lapBtn = document.getElementById('sw-lap-btn');
    const resetBtn = document.getElementById('sw-reset-btn');
    const lapsWrap = document.getElementById('sw-laps');
    const lapsList = document.getElementById('sw-laps-list');

    let elapsed = 0;
    let startStamp = 0;
    let rafId = null;
    const laps = [];

    const pad = (n) => String(n).padStart(2, '0');

    function format(ms, withCenti) {
        const totalSec = Math.floor(ms / 1000);
        const min = Math.floor(totalSec / 60);
        const sec = totalSec % 60;
        const centi = Math.floor((ms % 1000) / 10);
        return withCenti
            ? { min: pad(min), sec: pad(sec), centi: pad(centi) }
            : `${pad(min)}:${pad(sec)}.${pad(centi)}`;
    }

    function render() {
        const t = format(elapsed, true);
        displayMin.textContent = t.min;
        displaySec.textContent = t.sec;
        displayCenti.textContent = t.centi;
    }

    function tick() {
        elapsed += performance.now() - startStamp;
        startStamp = performance.now();
        render();
        rafId = requestAnimationFrame(tick);
    }

    function setRunning(running) {
        if (running) {
            startStamp = performance.now();
            rafId = requestAnimationFrame(tick);
            startBtn.textContent = 'Pause';
            lapBtn.disabled = false;
        } else {
            cancelAnimationFrame(rafId);
            rafId = null;
            startBtn.textContent = 'Resume';
            lapBtn.disabled = true;
        }
        resetBtn.disabled = false;
    }

    function addLap() {
        const prevTotal = laps.length ? laps[laps.length - 1].total : 0;
        laps.push({ total: elapsed, split: elapsed - prevTotal });
        renderLaps();
    }

    function renderLaps() {
        lapsList.innerHTML = '';
        const splits = laps.map((l) => l.split);
        const best = Math.min(...splits);
        const worst = Math.max(...splits);
        for (let i = laps.length - 1; i >= 0; i--) {
            const li = document.createElement('li');
            if (laps.length > 1) {
                if (splits[i] === best) li.classList.add('best');
                if (splits[i] === worst) li.classList.add('worst');
            }
            li.innerHTML =
                `<span>Lap ${i + 1}</span>` +
                `<span>${format(splits[i])}</span>` +
                `<span>${format(laps[i].total)}</span>`;
            lapsList.appendChild(li);
        }
        lapsWrap.hidden = laps.length === 0;
    }

    function reset() {
        cancelAnimationFrame(rafId);
        rafId = null;
        if (elapsed >= 5000) window.logSession('stopwatch', elapsed / 1000);
        elapsed = 0;
        laps.length = 0;
        render();
        renderLaps();
        startBtn.textContent = 'Start';
        lapBtn.disabled = true;
        resetBtn.disabled = true;
    }

    startBtn.addEventListener('click', () => setRunning(rafId === null));
    lapBtn.addEventListener('click', addLap);
    resetBtn.addEventListener('click', reset);

    // Auto-save elapsed time if the tab is closed mid-run
    window.addEventListener('pagehide', () => {
        if (rafId !== null) {
            elapsed += performance.now() - startStamp;
        }
        if (elapsed >= 5000) window.logSession('stopwatch', elapsed / 1000);
    });

    // Space = start/pause, L = lap
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') { e.preventDefault(); setRunning(rafId === null); }
        if (e.code === 'KeyL' && rafId !== null) addLap();
    });

    render();
})();
