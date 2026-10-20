(function () {
    'use strict';

    var btn = document.getElementById('theme-toggle');
    if (!btn) return;

    var MOON = '☾';
    var SUN = '☀';

    function apply(theme) {
        document.body.dataset.theme = theme;
        localStorage.setItem('theme', theme);
        btn.textContent = theme === 'dark' ? SUN : MOON;
        document.dispatchEvent(new CustomEvent('themechange', { detail: theme }));
    }

    btn.addEventListener('click', function () {
        apply(document.body.dataset.theme === 'dark' ? 'light' : 'dark');
    });

    btn.textContent = document.body.dataset.theme === 'dark' ? SUN : MOON;

    // Progress bars: fill width comes from data-pct (avoids template vars in inline styles)
    document.querySelectorAll('.todo-bar-fill[data-pct]').forEach(function (el) {
        el.style.width = el.dataset.pct + '%';
    });

    // "Session saved" toast after a timer session is logged
    document.addEventListener('sessionsaved', function () {
        var toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = 'Session saved to your report ✓';
        document.body.appendChild(toast);
        requestAnimationFrame(function () { toast.classList.add('show'); });
        setTimeout(function () {
            toast.classList.remove('show');
            setTimeout(function () { toast.remove(); }, 400);
        }, 2600);
    });
})();
